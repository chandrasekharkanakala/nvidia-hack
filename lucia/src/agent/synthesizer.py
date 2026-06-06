"""LUCIA Agent — Final response generation with streaming."""

import logging
from typing import Callable

from openai import AsyncOpenAI

from config.settings import settings
from src.agent.prompts import SYNTHESIZER_DEEP, SYNTHESIZER_LIGHT

logger = logging.getLogger(__name__)

client = AsyncOpenAI(base_url=settings.vllm_base_url, api_key="not-needed")


def _build_context(tool_results: list[dict]) -> str:
    """Format tool results as numbered sources for citation."""
    sources = []
    for i, r in enumerate(tool_results):
        if r["success"] and r["data"] is not None:
            data_str = str(r["data"])[:1000]
            sources.append(f"[{i+1}] Source ({r['tool']}): {data_str}")
    return "\n\n".join(sources) if sources else "No tool results available."


async def generate(
    query: str,
    tool_results: list[dict],
    history: list[dict],
    mode: str,
    on_token: Callable | None = None,
) -> str:
    """Generate the final response, streaming tokens via on_token callback.

    Uses SYNTHESIZER_LIGHT or SYNTHESIZER_DEEP based on mode.
    """
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
        stream = await client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=temperature,
            max_tokens=1024,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_response += token
                if on_token:
                    try:
                        await on_token(token)
                    except Exception:
                        pass

        return full_response.strip() if full_response else "I wasn't able to generate a response. Please try again."

    except Exception as e:
        logger.error(f"Synthesizer failed: {e}")
        return "I encountered an error generating a response. Please try again."
