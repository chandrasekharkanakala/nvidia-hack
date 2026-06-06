"""LUCIA Agent — Intent classification via LLM."""

import json
import logging

from openai import AsyncOpenAI

from config.settings import settings
from src.agent.prompts import ROUTER_SYSTEM

logger = logging.getLogger(__name__)

client = AsyncOpenAI(base_url=settings.vllm_base_url, api_key="not-needed")


async def classify(
    message: str, history: list[dict], has_image: bool = False
) -> dict:
    """Classify user intent and suggest tool routing.

    Returns: {intent: str, tool_hint: str|None, mode_override: str|None}
    """
    if has_image:
        return {"intent": "vision", "tool_hint": "vision", "mode_override": None}

    try:
        messages = [{"role": "system", "content": ROUTER_SYSTEM}]
        for msg in history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": message})

        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=0,
            max_tokens=100,
        )

        raw = response.choices[0].message.content.strip()
        # Extract JSON from response
        if "{" in raw:
            raw = raw[raw.index("{"):raw.rindex("}") + 1]
        result = json.loads(raw)

        intent = result.get("intent", "simple_qa")
        tool_hint = result.get("tool_hint")

        # Mode override: analysis queries should use deep mode
        mode_override = None
        if intent == "analysis":
            mode_override = "deep"

        return {
            "intent": intent,
            "tool_hint": tool_hint,
            "mode_override": mode_override,
        }

    except Exception as e:
        logger.warning(f"Router classification failed: {e}")
        return {"intent": "simple_qa", "tool_hint": None, "mode_override": None}
