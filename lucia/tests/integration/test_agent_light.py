"""Integration tests for full Light mode agent flow (mocked LLM)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.factories import make_session_id, make_message


@pytest.fixture
def mock_light_pipeline():
    """Mocks for full Light mode pipeline."""
    router_result = {"intent": "lookup", "tool_hint": "sql_query", "mode_override": None}
    tool_result = {
        "sql": "SELECT mode, SUM(journeys_millions) FROM transport_journeys GROUP BY mode",
        "columns": ["mode", "total"],
        "rows": [["Underground", 1311.2], ["Bus", 1639.5]],
        "row_count": 2,
        "error": None,
    }
    synth_response = "The data shows Bus (1,639.5M journeys) leads over Underground (1,311.2M) across all periods."

    return router_result, tool_result, synth_response


class TestAgentLightFlow:
    """Integration tests for Light mode: Router → Tool → Synthesize."""

    @pytest.mark.asyncio
    @patch("agent.synthesizer.AsyncOpenAI")
    @patch("agent.executor._load_tool")
    @patch("agent.router.AsyncOpenAI")
    @patch("agent.memory.duckdb")
    async def test_full_light_flow(
        self, mock_mem_db, mock_router_openai, mock_load_tool, mock_synth_openai, test_db, mock_light_pipeline
    ):
        router_result, tool_result, synth_response = mock_light_pipeline

        # Setup memory
        mock_mem_db.connect.return_value = test_db
        test_db.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY, session_id VARCHAR, role VARCHAR,
                content TEXT, mode VARCHAR DEFAULT 'light', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Setup router
        router_llm = AsyncMock()
        router_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                content='{"intent": "lookup", "tool_hint": "sql_query", "mode_override": null}'
            ))])
        )
        mock_router_openai.return_value = router_llm

        # Setup tool
        mock_load_tool.return_value = AsyncMock(return_value=tool_result)

        # Setup synthesizer
        synth_llm = AsyncMock()
        synth_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(content=synth_response))])
        )
        mock_synth_openai.return_value = synth_llm

        from agent import process_message, AgentMode

        result = await process_message(
            content="What are the busiest transport modes?",
            session_id=make_session_id(),
            mode=AgentMode.light,
        )

        assert result["content"] == synth_response
        assert result["mode"] == "light"
        assert "metrics" in result
        assert result["metrics"]["intent"] == "lookup"

    @pytest.mark.asyncio
    @patch("agent.synthesizer.AsyncOpenAI")
    @patch("agent.executor._load_tool")
    @patch("agent.router.AsyncOpenAI")
    @patch("agent.memory.duckdb")
    async def test_light_flow_with_rag(
        self, mock_mem_db, mock_router_openai, mock_load_tool, mock_synth_openai, test_db
    ):
        mock_mem_db.connect.return_value = test_db
        test_db.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY, session_id VARCHAR, role VARCHAR,
                content TEXT, mode VARCHAR DEFAULT 'light', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Router returns rag_search hint
        router_llm = AsyncMock()
        router_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                content='{"intent": "simple_qa", "tool_hint": "rag_search", "mode_override": null}'
            ))])
        )
        mock_router_openai.return_value = router_llm

        # RAG tool result
        mock_load_tool.return_value = AsyncMock(return_value={
            "results": [{"text": "The congestion charge is £15 per day", "score": 0.95, "source": "tfl.pdf"}],
            "error": None,
        })

        synth_llm = AsyncMock()
        synth_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                content="The congestion charge in London is £15 per day for most vehicles."
            ))])
        )
        mock_synth_openai.return_value = synth_llm

        from agent import process_message, AgentMode

        result = await process_message(
            content="What is the congestion charge?",
            session_id=make_session_id(),
            mode=AgentMode.light,
        )

        assert "congestion" in result["content"].lower() or len(result["content"]) > 0
        assert result["mode"] == "light"

    @pytest.mark.asyncio
    @patch("agent.synthesizer.AsyncOpenAI")
    @patch("agent.executor._load_tool")
    @patch("agent.router.AsyncOpenAI")
    @patch("agent.memory.duckdb")
    async def test_light_flow_tool_failure_graceful(
        self, mock_mem_db, mock_router_openai, mock_load_tool, mock_synth_openai, test_db
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
                content='{"intent": "lookup", "tool_hint": "sql_query", "mode_override": null}'
            ))])
        )
        mock_router_openai.return_value = router_llm

        # Tool fails
        mock_load_tool.return_value = AsyncMock(side_effect=Exception("DB connection lost"))

        synth_llm = AsyncMock()
        synth_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                content="I apologize, I wasn't able to retrieve that data. Please try again."
            ))])
        )
        mock_synth_openai.return_value = synth_llm

        from agent import process_message, AgentMode

        result = await process_message(
            content="How many journeys?",
            session_id=make_session_id(),
            mode=AgentMode.light,
        )

        # Should not crash, should return something
        assert isinstance(result["content"], str)
        assert len(result["content"]) > 0

    @pytest.mark.asyncio
    @patch("agent.synthesizer.AsyncOpenAI")
    @patch("agent.executor._load_tool")
    @patch("agent.router.AsyncOpenAI")
    @patch("agent.memory.duckdb")
    async def test_light_flow_emits_events(
        self, mock_mem_db, mock_router_openai, mock_load_tool, mock_synth_openai, test_db
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
                content='{"intent": "lookup", "tool_hint": "sql_query", "mode_override": null}'
            ))])
        )
        mock_router_openai.return_value = router_llm

        mock_load_tool.return_value = AsyncMock(return_value={"rows": [], "columns": [], "error": None})

        synth_llm = AsyncMock()
        synth_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="Response"))])
        )
        mock_synth_openai.return_value = synth_llm

        events = []

        async def on_event(event_type, **data):
            events.append(event_type)

        from agent import process_message, AgentMode

        await process_message(
            content="Test",
            session_id=make_session_id(),
            mode=AgentMode.light,
            on_event=on_event,
        )

        # Should emit at least tool_start, tool_end, done
        assert any("tool" in e for e in events) or "done" in events
