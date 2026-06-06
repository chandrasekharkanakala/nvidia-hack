"""LUCIA Agent — Query decomposition into tool call plans (Deep mode)."""

import json
import logging

from openai import AsyncOpenAI

from config.settings import settings
from agent.prompts import PLANNER_SYSTEM

logger = logging.getLogger(__name__)


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
        # Extract JSON array
        if "[" in raw:
            raw = raw[raw.index("["):raw.rindex("]") + 1]
        steps = json.loads(raw)

        if not isinstance(steps, list):
            steps = [steps]

        # Enforce max steps
        steps = steps[: settings.deep_max_steps]

        # Validate step structure
        validated = []
        for step in steps:
            validated.append({
                "tool": step.get("tool", "rag_search"),
                "params": step.get("params", {}),
                "depends_on": step.get("depends_on"),
            })

        return validated

    except Exception as e:
        logger.warning(f"Planner failed: {e}")
        # Fallback: single RAG search
        return [{"tool": "rag_search", "params": {"query": message}, "depends_on": None}]
