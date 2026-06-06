"""Unit tests for the Router (intent classification)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.factories import make_message, make_session_id


@pytest.fixture
def mock_router_llm():
    """LLM mock that returns JSON intent classification."""
    mock = AsyncMock()

    def make_response(content: str):
        return MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(content=content),
                    finish_reason="stop",
                )
            ]
        )

    mock.chat.completions.create = AsyncMock(
        return_value=make_response('{"intent": "lookup", "tool_hint": "sql_query", "mode_override": null}')
    )
    return mock


class TestRouterClassify:
    """Tests for router.classify() intent classification."""

    @pytest.mark.asyncio
    @patch("agent.router.AsyncOpenAI")
    async def test_simple_query_returns_lookup(self, mock_openai_cls, mock_router_llm):
        mock_openai_cls.return_value = mock_router_llm
        from agent.router import classify

        result = await classify("How many bus journeys in 2023?", [])

        assert result["intent"] == "lookup"
        assert result["tool_hint"] == "sql_query"
        assert result["mode_override"] is None

    @pytest.mark.asyncio
    @patch("agent.router.AsyncOpenAI")
    async def test_analysis_query_triggers_deep_mode(self, mock_openai_cls):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='{"intent": "analysis", "tool_hint": "sql_query", "mode_override": "deep"}'
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        from agent.router import classify

        result = await classify(
            "Compare air quality trends across all boroughs and correlate with transport usage", []
        )

        assert result["intent"] == "analysis"
        assert result["mode_override"] == "deep"

    @pytest.mark.asyncio
    @patch("agent.router.AsyncOpenAI")
    async def test_vision_intent_when_image_present(self, mock_openai_cls):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='{"intent": "vision", "tool_hint": "vision", "mode_override": null}'
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        from agent.router import classify

        result = await classify("What's in this image?", [], has_image=True)

        assert result["intent"] == "vision"
        assert result["tool_hint"] == "vision"

    @pytest.mark.asyncio
    @patch("agent.router.AsyncOpenAI")
    async def test_simulation_intent(self, mock_openai_cls):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='{"intent": "simulation", "tool_hint": "simulator", "mode_override": "deep"}'
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        from agent.router import classify

        result = await classify("Simulate closing the A40 for 3 hours during rush hour", [])

        assert result["intent"] == "simulation"
        assert result["tool_hint"] == "simulator"

    @pytest.mark.asyncio
    @patch("agent.router.AsyncOpenAI")
    async def test_prediction_intent(self, mock_openai_cls):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='{"intent": "prediction", "tool_hint": "predictor", "mode_override": null}'
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        from agent.router import classify

        result = await classify("Predict traffic on the M25 for the next 24 hours", [])

        assert result["intent"] == "prediction"
        assert result["tool_hint"] == "predictor"

    @pytest.mark.asyncio
    @patch("agent.router.AsyncOpenAI")
    async def test_history_passed_to_llm(self, mock_openai_cls):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='{"intent": "lookup", "tool_hint": "rag_search", "mode_override": null}'
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        from agent.router import classify

        history = [
            {"role": "user", "content": "Tell me about cycling"},
            {"role": "assistant", "content": "Cycling is growing in London."},
        ]
        await classify("What about last year specifically?", history)

        call_args = llm.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages", [])
        # Should include history context (system + history + user)
        assert len(messages) >= 3

    @pytest.mark.asyncio
    @patch("agent.router.AsyncOpenAI")
    async def test_malformed_llm_response_uses_fallback(self, mock_openai_cls):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content="not valid json at all"))]
            )
        )
        mock_openai_cls.return_value = llm
        from agent.router import classify

        result = await classify("Hello there", [])

        # Should return a valid dict even on parse failure
        assert "intent" in result
        assert isinstance(result["intent"], str)

    @pytest.mark.asyncio
    @patch("agent.router.AsyncOpenAI")
    async def test_simple_qa_intent(self, mock_openai_cls):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='{"intent": "simple_qa", "tool_hint": "rag_search", "mode_override": null}'
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        from agent.router import classify

        result = await classify("What is the congestion charge?", [])

        assert result["intent"] == "simple_qa"
        assert result["tool_hint"] == "rag_search"
