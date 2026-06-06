"""LUCIA Agent — Query decomposition into tool call plans (Deep mode)."""

import json
import logging
import re

from openai import AsyncOpenAI

from config.settings import settings
from agent.prompts import PLANNER_SYSTEM

logger = logging.getLogger(__name__)


def _extract_json_array(text: str) -> list | None:
    """Robustly extract a JSON array from LLM output."""
    # Try direct parse
    try:
        result = json.loads(text)
        return result if isinstance(result, list) else [result]
    except (json.JSONDecodeError, ValueError):
        pass

    # Try extracting JSON array
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            return result if isinstance(result, list) else [result]
        except (json.JSONDecodeError, ValueError):
            pass

    # Try from markdown code block
    match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # Last resort: find individual tool objects
    objects = re.findall(r'\{[^{}]*"tool"[^{}]*\}', text)
    if objects:
        steps = []
        for obj in objects:
            try:
                steps.append(json.loads(obj))
            except (json.JSONDecodeError, ValueError):
                pass
        if steps:
            return steps

    return None


async def create_plan(
    message: str, intent: str, history: list[dict]
) -> list[dict]:
    """Decompose a query into ordered tool call steps (max 5).

    Returns: list of {tool: str, params: dict, depends_on: int|None}
    """
    try:
        client = AsyncOpenAI(base_url=settings.vllm_base_url, api_key="not-needed")

        messages = [{"role": "system", "content": PLANNER_SYSTEM}]
        for msg in history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({
            "role": "user",
            "content": f"Intent: {intent}\nQuery: {message}",
        })

        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=settings.deep_temperature,
            max_tokens=500,
        )

        raw = response.choices[0].message.content.strip()
        steps = _extract_json_array(raw)

        if steps is None:
            logger.warning(f"Planner: could not parse JSON from: {raw[:100]}")
            return [{"tool": "sql_query", "params": {"query": message}, "depends_on": None}]

        # Enforce max steps
        steps = steps[: settings.deep_max_steps]

        # Validate step structure
        validated = []
        for step in steps:
            validated.append({
                "tool": step.get("tool", "rag_search"),
                "params": step.get("params", {"query": message}),
                "depends_on": step.get("depends_on"),
            })

        return validated

    except Exception as e:
        logger.warning(f"Planner failed: {e}")
        return [{"tool": "sql_query", "params": {"query": message}, "depends_on": None}]
