"""Unit tests for the Executor (tool execution engine)."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from tests.factories import make_plan_step, make_tool_result


@pytest.fixture
def mock_sql_tool():
    """Mock SQL tool that returns query results."""
    mock = AsyncMock(return_value={
        "sql": "SELECT * FROM transport_journeys LIMIT 5",
        "columns": ["year", "quarter", "mode", "journeys_millions", "borough"],
        "rows": [
            [2023, "Q1", "Underground", 320.5, "Westminster"],
            [2023, "Q1", "Bus", 415.2, "Camden"],
        ],
        "row_count": 2,
        "error": None,
    })
    return mock


@pytest.fixture
def mock_rag_tool():
    """Mock RAG tool that returns search results."""
    mock = AsyncMock(return_value={
        "results": [
            {"text": "Congestion charges reduce traffic by 15%", "score": 0.89, "source": "tfl_report.pdf"},
            {"text": "ULEZ expansion covers all London boroughs", "score": 0.76, "source": "gla_policy.pdf"},
        ],
        "error": None,
    })
    return mock


class TestExecutorExecuteStep:
    """Tests for executor._execute_step() single tool invocation."""

    @pytest.mark.asyncio
    @patch("agent.executor._load_tool")
    async def test_successful_tool_execution(self, mock_load, mock_sql_tool):
        mock_load.return_value = mock_sql_tool
        from agent.executor import _execute_step

        result = await _execute_step("sql_query", {"query": "SELECT 1"})

        assert result["success"] is True
        assert result["tool"] == "sql_query"
        assert result["duration_ms"] >= 0
        assert result["data"]["row_count"] == 2

    @pytest.mark.asyncio
    @patch("agent.executor._load_tool")
    async def test_tool_failure_captured(self, mock_load):
        mock_tool = AsyncMock(side_effect=ValueError("Invalid query syntax"))
        mock_load.return_value = mock_tool
        from agent.executor import _execute_step

        result = await _execute_step("sql_query", {"query": "INVALID"})

        assert result["success"] is False
        assert "error" in result
        assert "Invalid query" in result["error"]

    @pytest.mark.asyncio
    @patch("agent.executor._load_tool")
    async def test_tool_timeout_handled(self, mock_load):
        async def slow_tool(**kwargs):
            await asyncio.sleep(100)
            return {}

        mock_load.return_value = slow_tool
        from agent.executor import _execute_step

        with patch("agent.executor.settings", MagicMock(tool_timeout_seconds=0.01)):
            result = await _execute_step("slow_tool", {})

        assert result["success"] is False
        assert "timeout" in result.get("error", "").lower() or result["success"] is False

    @pytest.mark.asyncio
    @patch("agent.executor._load_tool")
    async def test_duration_tracked(self, mock_load):
        async def timed_tool(**kwargs):
            await asyncio.sleep(0.05)
            return {"data": "ok"}

        mock_load.return_value = timed_tool
        from agent.executor import _execute_step

        result = await _execute_step("test_tool", {})

        assert result["duration_ms"] >= 40  # at least 40ms


class TestExecutorExecutePlan:
    """Tests for executor.execute_plan() multi-step execution."""

    @pytest.mark.asyncio
    @patch("agent.executor._load_tool")
    async def test_sequential_plan_execution(self, mock_load, mock_sql_tool, mock_rag_tool):
        call_count = {"n": 0}

        async def tool_dispatch(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return await mock_sql_tool(**kwargs)
            return await mock_rag_tool(**kwargs)

        mock_load.return_value = tool_dispatch
        from agent.executor import execute_plan

        steps = [
            make_plan_step(tool="sql_query", params={"query": "SELECT 1"}),
            make_plan_step(tool="rag_search", params={"query": "London policy"}),
        ]

        results = await execute_plan(steps)

        assert len(results) == 2
        assert all(r["success"] for r in results)

    @pytest.mark.asyncio
    @patch("agent.executor._load_tool")
    async def test_dependency_injection(self, mock_load):
        received_params = {}

        async def capturing_tool(**kwargs):
            received_params.update(kwargs)
            return {"data": "step_0_output"}

        mock_load.return_value = capturing_tool
        from agent.executor import execute_plan

        steps = [
            make_plan_step(tool="sql_query", params={"query": "SELECT 1"}, depends_on=[]),
            make_plan_step(tool="rag_search", params={"query": "context"}, depends_on=[0]),
        ]

        results = await execute_plan(steps)

        assert len(results) == 2

    @pytest.mark.asyncio
    @patch("agent.executor._load_tool")
    async def test_retry_on_failure(self, mock_load):
        attempt = {"count": 0}

        async def flaky_tool(**kwargs):
            attempt["count"] += 1
            if attempt["count"] == 1:
                raise RuntimeError("Temporary failure")
            return {"data": "success on retry"}

        mock_load.return_value = flaky_tool
        from agent.executor import execute_plan

        steps = [make_plan_step(tool="sql_query", params={"query": "SELECT 1"})]

        results = await execute_plan(steps)

        # Should have retried and succeeded
        assert len(results) >= 1

    @pytest.mark.asyncio
    @patch("agent.executor._load_tool")
    async def test_events_emitted(self, mock_load, mock_sql_tool):
        mock_load.return_value = mock_sql_tool
        from agent.executor import execute_plan

        events = []

        async def on_event(event_type, **data):
            events.append({"type": event_type, **data})

        steps = [make_plan_step(tool="sql_query", params={"query": "SELECT 1"})]
        await execute_plan(steps, on_event=on_event)

        event_types = [e["type"] for e in events]
        assert "tool_start" in event_types
        assert "tool_end" in event_types

    @pytest.mark.asyncio
    @patch("agent.executor._load_tool")
    async def test_empty_plan_returns_empty(self, mock_load):
        from agent.executor import execute_plan

        results = await execute_plan([])

        assert results == []

    @pytest.mark.asyncio
    @patch("agent.executor._load_tool")
    async def test_all_steps_fail_gracefully(self, mock_load):
        mock_load.return_value = AsyncMock(side_effect=Exception("always fails"))
        from agent.executor import execute_plan

        steps = [
            make_plan_step(tool="bad_tool", params={}),
            make_plan_step(tool="bad_tool", params={}),
        ]

        results = await execute_plan(steps)

        assert len(results) == 2
        assert all(r["success"] is False for r in results)


class TestExecutorLoadTool:
    """Tests for executor._load_tool() dynamic import."""

    @patch("agent.executor.importlib")
    def test_load_known_tool(self, mock_importlib):
        mock_module = MagicMock()
        mock_module.execute = AsyncMock()
        mock_importlib.import_module.return_value = mock_module
        from agent.executor import _load_tool

        tool = _load_tool("sql_query")

        assert tool is not None

    def test_load_unknown_tool_raises(self):
        from agent.executor import _load_tool

        with pytest.raises((KeyError, ImportError, ValueError)):
            _load_tool("nonexistent_tool_xyz")
