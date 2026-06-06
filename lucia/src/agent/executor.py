"""LUCIA Agent — Tool execution engine with retry and timeout."""

import asyncio
import importlib
import logging
import time
from typing import Any, Callable

from config.settings import settings

logger = logging.getLogger(__name__)

TOOL_MODULE_MAP = {
    "rag_search": "tools.rag_search",
    "sql_query": "tools.sql_query",
    "web_scraper": "tools.web_scraper",
    "simulator": "tools.simulator",
    "predictor": "tools.predictor",
    "vision": "tools.vision",
    "calculator": "tools.calculator",
}


def _load_tool(tool_name: str) -> Any:
    """Dynamically import a tool module and return its execute function."""
    module_path = TOOL_MODULE_MAP.get(tool_name)
    if not module_path:
        raise ValueError(f"Unknown tool: {tool_name}")
    module = importlib.import_module(module_path)
    if not hasattr(module, "execute"):
        raise AttributeError(f"Tool module {module_path} has no 'execute' function")
    return module.execute


async def _execute_step(tool_name: str, params: dict) -> dict:
    """Execute a single tool with timeout."""
    start = time.perf_counter()
    try:
        run_fn = _load_tool(tool_name)
        result = await asyncio.wait_for(
            run_fn(**params),
            timeout=settings.tool_timeout_seconds,
        )
        duration_ms = (time.perf_counter() - start) * 1000
        return {
            "tool": tool_name,
            "success": True,
            "data": result,
            "duration_ms": round(duration_ms, 1),
            "error": None,
        }
    except asyncio.TimeoutError:
        duration_ms = (time.perf_counter() - start) * 1000
        return {
            "tool": tool_name,
            "success": False,
            "data": None,
            "duration_ms": round(duration_ms, 1),
            "error": f"Tool '{tool_name}' timed out after {settings.tool_timeout_seconds}s",
        }
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        return {
            "tool": tool_name,
            "success": False,
            "data": None,
            "duration_ms": round(duration_ms, 1),
            "error": str(e),
        }


async def execute_plan(
    steps: list[dict], on_event: Callable | None = None
) -> list[dict]:
    """Execute a list of tool call steps in order, respecting dependencies.

    Emits tool_start/tool_end events via on_event callback.
    Retries once on failure; skips after second failure.
    """
    results: list[dict] = []

    for i, step in enumerate(steps):
        tool_name = step["tool"]
        params = dict(step.get("params", {}))

        # Inject dependency output into params if applicable
        depends_on = step.get("depends_on")
        if depends_on is not None and 0 <= depends_on < len(results):
            dep_result = results[depends_on]
            if dep_result["success"] and dep_result["data"] is not None:
                params["context"] = dep_result["data"]

        # Emit tool_start
        if on_event:
            try:
                await on_event({"type": "tool_start", "tool": tool_name, "step": i})
            except Exception:
                pass

        # Execute with retry
        result = await _execute_step(tool_name, params)

        if not result["success"]:
            logger.info(f"Retrying tool '{tool_name}' (step {i})")
            result = await _execute_step(tool_name, params)

        results.append(result)

        # Emit tool_end
        if on_event:
            try:
                await on_event({
                    "type": "tool_end",
                    "tool": tool_name,
                    "step": i,
                    "success": result["success"],
                    "duration_ms": result["duration_ms"],
                })
            except Exception:
                pass

    return results
