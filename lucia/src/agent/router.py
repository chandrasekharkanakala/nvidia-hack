"""LUCIA Agent — Intent classification via LLM."""

import json
import logging
import re

from openai import AsyncOpenAI

from config.settings import settings
from agent.prompts import ROUTER_SYSTEM

logger = logging.getLogger(__name__)

# Fast-path patterns — skip LLM entirely for obvious intents
_CHITCHAT_PATTERNS = (
    "hello", "hi", "hey", "thanks", "thank you", "good morning",
    "good evening", "good afternoon", "what can you do", "what can you help",
    "who are you", "how are you", "bye", "goodbye", "cheers",
)

_LOOKUP_PATTERNS = (
    "how many", "how much", "total", "count", "average", "sum",
    "show me", "list", "top", "bottom", "highest", "lowest",
    "which borough", "what is the", "compare",
)

_REALTIME_PATTERNS = (
    "current", "right now", "today", "live", "real-time", "status",
    "disruption", "weather", "forecast today", "tube status",
)

_VIZ_PATTERNS = (
    "chart", "plot", "graph", "visualize", "visualise", "draw",
    "show me a chart", "bar chart", "pie chart", "line chart",
)

_ANALYSIS_PATTERNS = (
    "correlat", "trend", "relationship", "compare across",
    "year over year", "yoy", "outlier", "anomal", "statistical",
    "join", "cross-table", "across datasets",
)

_SEARCH_PATTERNS = (
    "search for", "find information", "look up online", "what does",
    "latest news", "recent developments",
)


def _fast_classify(message: str) -> dict | None:
    """Keyword-based fast-path classification. Returns None if unsure."""
    lower = message.lower().strip()

    # Chitchat
    if any(lower.startswith(p) or lower == p for p in _CHITCHAT_PATTERNS):
        return {"intent": "chitchat", "tool_hint": None, "mode_override": None}

    # Visualization
    if any(p in lower for p in _VIZ_PATTERNS):
        return {"intent": "visualization", "tool_hint": "visualizer", "mode_override": None}

    # Deep analysis / cross-table
    if any(p in lower for p in _ANALYSIS_PATTERNS):
        return {"intent": "analysis", "tool_hint": "analyzer", "mode_override": "deep"}

    # Web search
    if any(p in lower for p in _SEARCH_PATTERNS):
        return {"intent": "web_search", "tool_hint": "web_search", "mode_override": None}

    # Real-time data
    if any(p in lower for p in _REALTIME_PATTERNS):
        return {"intent": "lookup", "tool_hint": "web_scraper", "mode_override": None}

    # Data lookup (SQL)
    if any(lower.startswith(p) or p in lower for p in _LOOKUP_PATTERNS):
        return {"intent": "lookup", "tool_hint": "sql_query", "mode_override": None}

    # Simulation
    if "simulate" in lower or "what if" in lower or "scenario" in lower:
        return {"intent": "simulation", "tool_hint": "simulator", "mode_override": "deep"}

    # Prediction
    if "predict" in lower or "forecast" in lower or "next week" in lower or "next month" in lower:
        return {"intent": "prediction", "tool_hint": "predictor", "mode_override": None}

    return None


def _extract_json(text: str) -> dict | None:
    """Robustly extract JSON from LLM output, handling markdown and extra text."""
    # Try direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try extracting JSON object with regex
    match = re.search(r'\{[^{}]*"intent"[^{}]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except (json.JSONDecodeError, ValueError):
            pass

    # Try extracting from markdown code block
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # Last resort: look for intent keyword in text
    intent_match = re.search(r'"intent"\s*:\s*"(\w+)"', text)
    tool_match = re.search(r'"tool_hint"\s*:\s*"(\w+)"', text)
    if intent_match:
        return {
            "intent": intent_match.group(1),
            "tool_hint": tool_match.group(1) if tool_match else None,
        }

    return None


async def classify(
    message: str, history: list[dict], has_image: bool = False
) -> dict:
    """Classify user intent and suggest tool routing.

    Returns: {intent: str, tool_hint: str|None, mode_override: str|None}
    """
    if has_image:
        return {"intent": "vision", "tool_hint": "vision", "mode_override": None}

    # Fast-path: keyword-based classification (no LLM call needed)
    fast = _fast_classify(message)
    if fast:
        logger.info(f"Router fast-path: {fast['intent']} (tool={fast['tool_hint']})")
        return fast

    try:
        client = AsyncOpenAI(base_url=settings.vllm_base_url, api_key="not-needed")

        messages = [{"role": "system", "content": ROUTER_SYSTEM}]
        for msg in history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": message})

        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=0,
            max_tokens=60,
        )

        raw = response.choices[0].message.content.strip()
        result = _extract_json(raw)

        if result is None:
            logger.warning(f"Router: could not parse JSON from: {raw[:100]}")
            return {"intent": "simple_qa", "tool_hint": "sql_query", "mode_override": None}

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
        return {"intent": "simple_qa", "tool_hint": "sql_query", "mode_override": None}
