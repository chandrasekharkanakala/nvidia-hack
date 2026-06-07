"""LUCIA Agent — Public API for the agent orchestration layer."""

import logging
import time
from enum import Enum
from typing import Any, Callable

from agent import executor, memory, planner, reflector, router, synthesizer

logger = logging.getLogger(__name__)


class AgentMode(str, Enum):
    light = "light"
    deep = "deep"


_GREETING_RESPONSE = """I'm LUCIA, your London city intelligence assistant, running on NVIDIA DGX Spark.

I can help you with:
• **Query 25+ London datasets** — transport, air quality, housing, crime, planning
• **Analyze trends** and correlations across boroughs
• **Real-time updates** — TfL disruptions, tube status, weather
• **Visualize data** — charts, maps, and comparisons
• **Simulate scenarios** — traffic changes, pollution impact

Try asking: "Which borough has the highest traffic volume?" or "Compare air quality across central London boroughs"."""


def _get_chitchat_response(message: str) -> str:
    """Return instant pre-built response for greetings/chitchat."""
    lower = message.lower().strip()
    if any(w in lower for w in ("who are you", "what are you", "what can you do", "what can you help")):
        return _GREETING_RESPONSE
    if any(w in lower for w in ("hello", "hi", "hey", "good morning", "good afternoon", "good evening")):
        return f"Hello! {_GREETING_RESPONSE}"
    if any(w in lower for w in ("thanks", "thank you", "cheers")):
        return "You're welcome! Let me know if you have any other questions about London's data."
    if any(w in lower for w in ("bye", "goodbye")):
        return "Goodbye! Feel free to come back anytime you need London data insights."
    if "how are you" in lower:
        return "I'm running well on DGX Spark! Ready to help you explore London's urban data. What would you like to know?"
    return _GREETING_RESPONSE


async def process_message(
    content: str,
    session_id: str,
    mode: AgentMode = AgentMode.light,
    image: bytes | None = None,
    on_event: Callable | None = None,
) -> dict:
    """Process a user message through the full agent pipeline.

    Flow: save user msg → load history → route → (plan if deep) → execute →
          (reflect if deep, retry once if low confidence) → synthesize →
          save assistant msg → return

    Returns: {content: str, mode: str, metrics: dict, tool_calls: list}
    """
    start_time = time.perf_counter()
    effective_mode = mode.value if hasattr(mode, "value") else str(mode)
    if effective_mode not in ("light", "deep"):
        effective_mode = "light"

    try:
        # Save user message
        await memory.save_message(session_id, "user", content, effective_mode)

        # Load history
        history = await memory.load_history(session_id)

        # Emit thinking event
        if on_event:
            await _safe_emit(on_event, {"type": "thinking", "stage": "routing"})

        # Route
        route_result = await router.classify(content, history, has_image=image is not None)
        intent = route_result["intent"]

        # Apply mode override from router
        if route_result.get("mode_override"):
            effective_mode = route_result["mode_override"]

        # Plan
        if intent in ("chitchat", "greeting"):
            # Instant response — no LLM call needed for greetings
            response_text = _get_chitchat_response(content)
            await memory.save_message(session_id, "assistant", response_text, effective_mode)
            total_ms = (time.perf_counter() - start_time) * 1000
            if on_event:
                for i in range(0, len(response_text), 20):
                    await _safe_emit(on_event, {"type": "token", "content": response_text[i:i+20]})
                await _safe_emit(on_event, {"type": "done", "metrics": {"total_ms": round(total_ms, 1)}})
            return {
                "content": response_text,
                "mode": effective_mode,
                "metrics": {"total_ms": round(total_ms, 1), "intent": intent, "steps": 0, "tools_succeeded": 0, "tools_failed": 0},
                "tool_calls": [],
            }
        elif effective_mode == "deep":
            # Deep mode: multi-tool pipeline (SQL + RAG + Analyzer)
            # Don't rely on LLM planner — use deterministic multi-step approach
            if on_event:
                await _safe_emit(on_event, {"type": "thinking", "stage": "planning"})
            steps = [
                {"tool": "sql_query", "params": {"query": content}, "depends_on": None},
                {"tool": "rag_search", "params": {"query": content}, "depends_on": None},
                {"tool": "analyzer", "params": {"query": content}, "depends_on": None},
            ]
        else:
            # Light mode: tool selection based on intent
            tool = route_result.get("tool_hint") or "sql_query"
            if intent == "visualization":
                steps = [{"tool": "visualizer", "params": {"query": content}, "depends_on": None}]
            elif intent == "analysis":
                # Analysis needs SQL + RAG for data, analyzer for insights
                steps = [
                    {"tool": "sql_query", "params": {"query": content}, "depends_on": None},
                    {"tool": "rag_search", "params": {"query": content}, "depends_on": None},
                ]
            elif intent == "web_search":
                steps = [{"tool": "web_search", "params": {"query": content}, "depends_on": None}]
            elif intent == "lookup" and tool == "web_scraper":
                steps = [
                    {"tool": "web_scraper", "params": {"query": content}, "depends_on": None},
                    {"tool": "rag_search", "params": {"query": content}, "depends_on": None},
                ]
            elif intent in ("lookup", "simple_qa"):
                # Use BOTH SQL + RAG for richer context
                steps = [
                    {"tool": "sql_query", "params": {"query": content}, "depends_on": None},
                    {"tool": "rag_search", "params": {"query": content}, "depends_on": None},
                ]
            elif intent == "vision" and image is not None:
                steps = [{"tool": "vision", "params": {"prompt": content, "image": image}, "depends_on": None}]
            else:
                # Default: SQL + RAG
                steps = [
                    {"tool": "sql_query", "params": {"query": content}, "depends_on": None},
                    {"tool": "rag_search", "params": {"query": content}, "depends_on": None},
                ]

        # Execute (skip if chitchat already set tool_results)
        if steps:
            tool_results = await executor.execute_plan(steps, on_event=on_event)

        # Reflect (deep mode only)
        metrics: dict[str, Any] = {}
        if effective_mode == "deep":
            if on_event:
                await _safe_emit(on_event, {"type": "thinking", "stage": "reflecting"})
            reflection = await reflector.validate(content, tool_results)
            metrics["reflection"] = reflection

            # Retry once if low confidence
            if reflection["retry"]:
                if on_event:
                    await _safe_emit(on_event, {"type": "thinking", "stage": "retrying"})
                tool_results = await executor.execute_plan(steps, on_event=on_event)
                reflection = await reflector.validate(content, tool_results)
                metrics["reflection_retry"] = reflection

        # Synthesize
        tokens: list[str] = []

        async def _on_token(token: str) -> None:
            tokens.append(token)
            if on_event:
                await _safe_emit(on_event, {"type": "token", "content": token})

        response_text = await synthesizer.generate(
            query=content,
            tool_results=tool_results,
            history=history,
            mode=effective_mode,
            on_token=_on_token,
        )

        # Save assistant message
        await memory.save_message(session_id, "assistant", response_text, effective_mode)

        # Metrics
        total_ms = (time.perf_counter() - start_time) * 1000
        metrics.update({
            "total_ms": round(total_ms, 1),
            "intent": intent,
            "steps": len(steps),
            "tools_succeeded": sum(1 for r in tool_results if r["success"]),
            "tools_failed": sum(1 for r in tool_results if not r["success"]),
        })

        # Emit done
        if on_event:
            await _safe_emit(on_event, {"type": "done", "metrics": metrics})

        return {
            "content": response_text,
            "mode": effective_mode,
            "metrics": metrics,
            "tool_calls": [
                {"tool": r["tool"], "success": r["success"], "duration_ms": r["duration_ms"]}
                for r in tool_results
            ],
        }

    except Exception as e:
        logger.error(f"Agent pipeline error: {e}", exc_info=True)
        error_msg = "I encountered a processing issue. Could you rephrase your question? Try asking about a specific borough, dataset, or metric."
        await memory.save_message(session_id, "assistant", error_msg, effective_mode)
        if on_event:
            await _safe_emit(on_event, {"type": "done", "error": str(e)})
        return {
            "content": error_msg,
            "mode": effective_mode,
            "metrics": {"error": str(e)},
            "tool_calls": [],
        }


async def _safe_emit(on_event: Callable, event: dict) -> None:
    """Emit an event without crashing on callback errors."""
    try:
        await on_event(event)
    except Exception:
        pass
