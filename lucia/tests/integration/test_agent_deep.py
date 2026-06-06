"""Integration tests for full Deep mode agent flow (mocked LLM)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.factories import make_session_id


class TestAgentDeepFlow:
    """Integration tests for Deep mode: Router → Planner → Executor → Reflector → Synthesize."""

    @pytest.mark.asyncio
    @patch("agent.synthesizer.AsyncOpenAI")
    @patch("agent.reflector.AsyncOpenAI")
    @patch("agent.executor._load_tool")
    @patch("agent.planner.AsyncOpenAI")
    @patch("agent.router.AsyncOpenAI")
    @patch("agent.memory.duckdb")
    async def test_full_deep_flow(
        self, mock_mem_db, mock_router_ai, mock_planner_ai, mock_load_tool,
        mock_reflector_ai, mock_synth_ai, test_db
    ):
        mock_mem_db.connect.return_value = test_db
        test_db.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY, session_id VARCHAR, role VARCHAR,
                content TEXT, mode VARCHAR DEFAULT 'light', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Router: classify as analysis → deep
        router_llm = AsyncMock()
        router_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                content='{"intent": "analysis", "tool_hint": "sql_query", "mode_override": "deep"}'
            ))])
        )
        mock_router_ai.return_value = router_llm

        # Planner: create multi-step plan
        planner_llm = AsyncMock()
        planner_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                content='''[
                    {"tool": "sql_query", "params": {"query": "SELECT borough, AVG(concentration) FROM air_quality GROUP BY borough"}, "depends_on": null},
                    {"tool": "sql_query", "params": {"query": "SELECT mode, SUM(journeys_millions) FROM transport_journeys GROUP BY mode"}, "depends_on": null},
                    {"tool": "rag_search", "params": {"query": "correlation transport air quality London"}, "depends_on": null}
                ]'''
            ))])
        )
        mock_planner_ai.return_value = planner_llm

        # Executor tools
        call_num = {"n": 0}

        async def mock_tool(**kwargs):
            call_num["n"] += 1
            if call_num["n"] <= 2:
                return {"rows": [[1, 2]], "columns": ["a", "b"], "error": None}
            return {"results": [{"text": "Studies show correlation", "score": 0.88}], "error": None}

        mock_load_tool.return_value = mock_tool

        # Reflector: high confidence
        reflector_llm = AsyncMock()
        reflector_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                content='{"confidence": 0.88, "grounded": true, "issues": [], "retry": false}'
            ))])
        )
        mock_reflector_ai.return_value = reflector_llm

        # Synthesizer
        synth_llm = AsyncMock()
        synth_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                content="Analysis shows a moderate correlation between transport usage and air quality. "
                        "Boroughs with higher bus usage tend to have elevated NO2 levels."
            ))])
        )
        mock_synth_ai.return_value = synth_llm

        from agent import process_message, AgentMode

        result = await process_message(
            content="Analyze the correlation between transport usage and air quality across London boroughs",
            session_id=make_session_id(),
            mode=AgentMode.deep,
        )

        assert result["mode"] == "deep"
        assert "correlation" in result["content"].lower() or len(result["content"]) > 50
        assert result["metrics"]["intent"] == "analysis"
        assert result["metrics"]["steps"] == 3

    @pytest.mark.asyncio
    @patch("agent.synthesizer.AsyncOpenAI")
    @patch("agent.reflector.AsyncOpenAI")
    @patch("agent.executor._load_tool")
    @patch("agent.planner.AsyncOpenAI")
    @patch("agent.router.AsyncOpenAI")
    @patch("agent.memory.duckdb")
    async def test_deep_flow_with_retry(
        self, mock_mem_db, mock_router_ai, mock_planner_ai, mock_load_tool,
        mock_reflector_ai, mock_synth_ai, test_db
    ):
        mock_mem_db.connect.return_value = test_db
        test_db.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY, session_id VARCHAR, role VARCHAR,
                content TEXT, mode VARCHAR DEFAULT 'light', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Router
        router_llm = AsyncMock()
        router_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                content='{"intent": "analysis", "tool_hint": null, "mode_override": "deep"}'
            ))])
        )
        mock_router_ai.return_value = router_llm

        # Planner
        planner_llm = AsyncMock()
        planner_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                content='[{"tool": "rag_search", "params": {"query": "test"}, "depends_on": null}]'
            ))])
        )
        mock_planner_ai.return_value = planner_llm

        # Tool
        mock_load_tool.return_value = AsyncMock(return_value={
            "results": [{"text": "Relevant data", "score": 0.5}], "error": None
        })

        # Reflector: first call low confidence (retry), second call passes
        reflector_calls = {"n": 0}
        reflector_llm = AsyncMock()

        async def reflector_side_effect(*args, **kwargs):
            reflector_calls["n"] += 1
            if reflector_calls["n"] == 1:
                return MagicMock(choices=[MagicMock(message=MagicMock(
                    content='{"confidence": 0.3, "grounded": false, "issues": ["Insufficient data"], "retry": true}'
                ))])
            return MagicMock(choices=[MagicMock(message=MagicMock(
                content='{"confidence": 0.75, "grounded": true, "issues": [], "retry": false}'
            ))])

        reflector_llm.chat.completions.create = AsyncMock(side_effect=reflector_side_effect)
        mock_reflector_ai.return_value = reflector_llm

        # Synthesizer
        synth_llm = AsyncMock()
        synth_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="Final answer after retry"))])
        )
        mock_synth_ai.return_value = synth_llm

        from agent import process_message, AgentMode

        result = await process_message(
            content="Deep analysis question",
            session_id=make_session_id(),
            mode=AgentMode.deep,
        )

        assert isinstance(result["content"], str)
        # Should have retried
        metrics = result.get("metrics", {})
        assert metrics.get("reflection_retry") is True or reflector_calls["n"] >= 2

    @pytest.mark.asyncio
    @patch("agent.synthesizer.AsyncOpenAI")
    @patch("agent.reflector.AsyncOpenAI")
    @patch("agent.executor._load_tool")
    @patch("agent.planner.AsyncOpenAI")
    @patch("agent.router.AsyncOpenAI")
    @patch("agent.memory.duckdb")
    async def test_deep_flow_mode_override_from_router(
        self, mock_mem_db, mock_router_ai, mock_planner_ai, mock_load_tool,
        mock_reflector_ai, mock_synth_ai, test_db
    ):
        """User requests light mode but router overrides to deep for complex query."""
        mock_mem_db.connect.return_value = test_db
        test_db.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY, session_id VARCHAR, role VARCHAR,
                content TEXT, mode VARCHAR DEFAULT 'light', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Router overrides to deep
        router_llm = AsyncMock()
        router_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                content='{"intent": "analysis", "tool_hint": "sql_query", "mode_override": "deep"}'
            ))])
        )
        mock_router_ai.return_value = router_llm

        planner_llm = AsyncMock()
        planner_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                content='[{"tool": "sql_query", "params": {"query": "SELECT 1"}, "depends_on": null}]'
            ))])
        )
        mock_planner_ai.return_value = planner_llm

        mock_load_tool.return_value = AsyncMock(return_value={"rows": [[1]], "columns": ["v"], "error": None})

        reflector_llm = AsyncMock()
        reflector_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                content='{"confidence": 0.9, "grounded": true, "issues": [], "retry": false}'
            ))])
        )
        mock_reflector_ai.return_value = reflector_llm

        synth_llm = AsyncMock()
        synth_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="Deep response"))])
        )
        mock_synth_ai.return_value = synth_llm

        from agent import process_message, AgentMode

        result = await process_message(
            content="Compare all boroughs transport and pollution data",
            session_id=make_session_id(),
            mode=AgentMode.light,  # User says light, router overrides
        )

        assert result["mode"] == "deep"

    @pytest.mark.asyncio
    @patch("agent.synthesizer.AsyncOpenAI")
    @patch("agent.executor._load_tool")
    @patch("agent.planner.AsyncOpenAI")
    @patch("agent.router.AsyncOpenAI")
    @patch("agent.memory.duckdb")
    async def test_deep_flow_metrics_tracked(
        self, mock_mem_db, mock_router_ai, mock_planner_ai, mock_load_tool, mock_synth_ai, test_db
    ):
        mock_mem_db.connect.return_value = test_db
        test_db.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY, session_id VARCHAR, role VARCHAR,
                content TEXT, mode VARCHAR DEFAULT 'light', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        router_llm = AsyncMock()
        router_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                content='{"intent": "simulation", "tool_hint": "simulator", "mode_override": "deep"}'
            ))])
        )
        mock_router_ai.return_value = router_llm

        planner_llm = AsyncMock()
        planner_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                content='[{"tool": "simulator", "params": {"road": "A40", "duration_hours": 2, "time_of_day": "17:00"}, "depends_on": null}]'
            ))])
        )
        mock_planner_ai.return_value = planner_llm

        mock_load_tool.return_value = AsyncMock(return_value={
            "affected_roads": ["A41", "A5"], "avg_delay_minutes": 12.5, "total_rerouted": 850, "recommendation": "Use A41"
        })

        synth_llm = AsyncMock()
        synth_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="Simulation complete"))])
        )
        mock_synth_ai.return_value = synth_llm

        from agent import process_message, AgentMode

        with patch("agent.reflector.AsyncOpenAI") as mock_ref_ai:
            ref_llm = AsyncMock()
            ref_llm.chat.completions.create = AsyncMock(
                return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                    content='{"confidence": 0.9, "grounded": true, "issues": [], "retry": false}'
                ))])
            )
            mock_ref_ai.return_value = ref_llm

            result = await process_message(
                content="Simulate A40 closure",
                session_id=make_session_id(),
                mode=AgentMode.deep,
            )

        metrics = result["metrics"]
        assert "total_ms" in metrics
        assert metrics["total_ms"] > 0
        assert metrics["tools_succeeded"] >= 1
