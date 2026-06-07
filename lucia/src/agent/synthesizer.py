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
        parts = []

        # RAG search results — extract only the text content
        if data.get("results") and isinstance(data["results"], list):
            results = data["results"]
            for item in results[:10]:
                if isinstance(item, dict):
                    # Extract actual text content, skip SQL/metadata
                    text = item.get("text", "")
                    if text and not text.strip().upper().startswith("SELECT"):
                        source = item.get("source", "")
                        parts.append(f"[From {source}]: {text[:300]}")
                    elif item.get("description"):
                        parts.append(item["description"][:300])
                else:
                    parts.append(str(item)[:200])
            if parts:
                return "\n".join(parts)

        # SQL query results — format as a readable table
        if data.get("rows") and data.get("columns"):
            cols = data["columns"]
            rows = data["rows"][:20]
            header = " | ".join(str(c) for c in cols)
            row_strs = [" | ".join(str(v) for v in row) for row in rows]
            table_str = f"{header}\n" + "\n".join(row_strs)
            if data.get("row_count", 0) > 20:
                table_str += f"\n... ({data['row_count']} total rows)"
            return table_str

        # SQL query with no rows but no error — report empty
        if "rows" in data and not data.get("rows") and not data.get("error"):
            return "No matching data found in the database."

        # Web scraper / live data
        if data.get("data") and data.get("source"):
            source = data["source"]
            live_data = data["data"]
            if isinstance(live_data, list):
                return f"[Live data from {source}]:\n" + "\n".join(str(d)[:200] for d in live_data[:10])
            elif isinstance(live_data, dict):
                return f"[Live data from {source}]: {str(live_data)[:500]}"

        # Generic structured results
        if data.get("summary"):
            parts.append(str(data["summary"]))
        if data.get("answer"):
            parts.append(str(data["answer"]))
        if data.get("content"):
            parts.append(str(data["content"]))

        # Fallback — exclude internal fields
        if not parts:
            exclude_keys = {"error", "sql", "query", "columns", "row_count", "fetched_at", "truncated"}
            cleaned = {k: v for k, v in data.items() if k not in exclude_keys and v}
            if cleaned:
                parts.append(str(cleaned)[:500])
        return "\n".join(parts) if parts else ""
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
