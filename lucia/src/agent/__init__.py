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
        if effective_mode == "deep":
            if on_event:
                await _safe_emit(on_event, {"type": "thinking", "stage": "planning"})
            steps = await planner.create_plan(content, intent, history)
        else:
            # Light mode: single tool call based on hint
            tool = route_result.get("tool_hint") or "rag_search"
            if intent == "simple_qa":
                steps = [{"tool": "rag_search", "params": {"query": content}, "depends_on": None}]
            elif intent == "vision" and image is not None:
                steps = [{"tool": "vision", "params": {"prompt": content, "image": image}, "depends_on": None}]
            else:
                steps = [{"tool": tool, "params": {"query": content}, "depends_on": None}]

        # Execute
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
        error_msg = "I'm sorry, I encountered an error processing your request. Please try again."
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
