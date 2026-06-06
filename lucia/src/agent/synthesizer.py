"""LUCIA Agent — Final response generation with streaming."""

import logging
from typing import Callable

from openai import AsyncOpenAI

from config.settings import settings
from agent.prompts import SYNTHESIZER_DEEP, SYNTHESIZER_LIGHT

logger = logging.getLogger(__name__)


def _extract_content(data) -> str:
    """Extract meaningful content from tool result data, stripping raw metadata."""
    if isinstance(data, dict):
        # Prefer summary or results fields over dumping the whole dict
        parts = []
        if data.get("summary"):
            parts.append(str(data["summary"]))
        if data.get("results"):
            results = data["results"]
            if isinstance(results, list):
                for item in results[:10]:
                    parts.append(str(item)[:200])
            else:
                parts.append(str(results)[:500])
        if data.get("answer"):
            parts.append(str(data["answer"]))
        if data.get("content"):
            parts.append(str(data["content"]))
        # Fallback: if no known fields matched, use a cleaned repr
        if not parts:
            cleaned = {k: v for k, v in data.items() if k not in ("error", "sources") and v}
            parts.append(str(cleaned)[:500])
        return "\n".join(parts)
    elif isinstance(data, list):
        return "\n".join(str(item)[:200] for item in data[:10])
    else:
        return str(data)[:1000]


def _build_context(tool_results: list[dict]) -> str:
    """Format tool results as numbered sources for citation."""
    sources = []
    idx = 1
    for r in tool_results:
        if r["success"] and r["data"] is not None:
            content = _extract_content(r["data"])
            if content.strip():
                sources.append(f"[{idx}] ({r['tool']}): {content}")
                idx += 1
    return "\n\n".join(sources) if sources else "No tool results available."


async def generate(
    query: str,
    tool_results: list[dict],
    history: list[dict],
    mode: str,
    on_token: Callable | None = None,
) -> str:
    """Generate the final response, streaming tokens via on_token callback."""
    client = AsyncOpenAI(base_url=settings.vllm_base_url, api_key="not-needed")

    system_prompt = SYNTHESIZER_DEEP if mode == "deep" else SYNTHESIZER_LIGHT
    context = _build_context(tool_results)
    temperature = settings.deep_temperature if mode == "deep" else settings.light_temperature

    messages = [{"role": "system", "content": system_prompt}]

    # Include recent history for conversational context
    for msg in history[-4:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({
        "role": "user",
        "content": f"{query}\n\n--- Retrieved Information ---\n{context}",
    })

    try:
        full_response = ""
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=temperature,
            max_tokens=1024,
            stream=True,
        )

        # Detect if response is streaming or non-streaming
        # Non-streaming: response.choices[0].message.content is a string
        # Streaming: response is an async iterator of chunks
        try:
            msg_content = response.choices[0].message.content
            if isinstance(msg_content, str):
                full_response = msg_content
            else:
                raise AttributeError("not a non-streaming response")
        except (AttributeError, IndexError, TypeError):
            # Streaming response (async iterator)
            try:
                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        full_response += token
                        if on_token:
                            try:
                                await on_token(token)
                            except Exception:
                                pass
            except (TypeError, AttributeError, StopAsyncIteration):
                pass

        return full_response.strip() if full_response else "I wasn't able to generate a response. Please try again."

    except Exception as e:
        logger.error(f"Synthesizer failed: {e}")
        return "I encountered an error generating a response. Please try again."
