"""Tool registry for LUCIA agent."""

import importlib
import logging

logger = logging.getLogger(__name__)

TOOLS = {"rag_search", "sql_query", "web_scraper", "simulator", "predictor", "vision", "calculator"}


async def call_tool(name: str, params: dict) -> dict:
    """Dynamic tool dispatch. Returns {success, data, error}."""
    if name not in TOOLS:
        return {"success": False, "data": None, "error": f"Unknown tool: {name}"}

    try:
        module = importlib.import_module(f".{name}", package="src.tools")
        result = await module.execute(**params)
        return {"success": True, "data": result, "error": None}
    except Exception as e:
        logger.exception(f"Tool '{name}' failed")
        return {"success": False, "data": None, "error": str(e)}
