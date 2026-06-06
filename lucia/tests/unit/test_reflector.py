"""Unit tests for the Reflector (response validation)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.factories import make_tool_result


@pytest.fixture
def successful_tool_results():
    """Tool results with high-quality data."""
    return [
        make_tool_result(
            tool="sql_query",
            success=True,
            data={"rows": [[2023, "Underground", 320.5]], "columns": ["year", "mode", "journeys"]},
            duration_ms=45.0,
        ),
        make_tool_result(
            tool="rag_search",
            success=True,
            data={"results": [{"text": "TfL reports 15% increase in cycling", "score": 0.92}]},
            duration_ms=120.0,
        ),
    ]


@pytest.fixture
def poor_tool_results():
    """Tool results with low-quality or failed data."""
    return [
        make_tool_result(tool="sql_query", success=False, data=None, duration_ms=5.0),
        make_tool_result(
            tool="rag_search",
            success=True,
            data={"results": [{"text": "Unrelated content about cooking", "score": 0.21}]},
            duration_ms=150.0,
        ),
    ]


class TestReflectorValidate:
    """Tests for reflector.validate() response quality check."""

    @pytest.mark.asyncio
    @patch("agent.reflector.AsyncOpenAI")
    async def test_high_confidence_grounded_response(self, mock_openai_cls, successful_tool_results):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='{"confidence": 0.92, "grounded": true, "issues": [], "retry": false}'
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        from agent.reflector import validate

        result = await validate("How many Underground journeys in 2023?", successful_tool_results)

        assert result["confidence"] >= 0.8
        assert result["grounded"] is True
        assert result["retry"] is False
        assert result["issues"] == []

    @pytest.mark.asyncio
    @patch("agent.reflector.AsyncOpenAI")
    async def test_low_confidence_triggers_retry(self, mock_openai_cls, poor_tool_results):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='{"confidence": 0.3, "grounded": false, "issues": ["SQL query failed", "RAG results irrelevant"], "retry": true}'
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        from agent.reflector import validate

        result = await validate("What is the air quality in Westminster?", poor_tool_results)

        assert result["confidence"] < 0.5
        assert result["grounded"] is False
        assert result["retry"] is True
        assert len(result["issues"]) > 0

    @pytest.mark.asyncio
    @patch("agent.reflector.AsyncOpenAI")
    async def test_partial_success_moderate_confidence(self, mock_openai_cls):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='{"confidence": 0.65, "grounded": true, "issues": ["Only partial data available"], "retry": false}'
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        from agent.reflector import validate

        results = [
            make_tool_result(tool="sql_query", success=True, data={"rows": [[1]], "columns": ["count"]}),
        ]

        result = await validate("Complex question", results)

        assert 0.5 <= result["confidence"] < 0.9
        assert result["retry"] is False

    @pytest.mark.asyncio
    @patch("agent.reflector.AsyncOpenAI")
    async def test_empty_results_low_confidence(self, mock_openai_cls):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='{"confidence": 0.1, "grounded": false, "issues": ["No tool results available"], "retry": true}'
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        from agent.reflector import validate

        result = await validate("What is the weather?", [])

        assert result["confidence"] < 0.5
        assert result["retry"] is True

    @pytest.mark.asyncio
    @patch("agent.reflector.AsyncOpenAI")
    async def test_malformed_llm_response_handled(self, mock_openai_cls):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content="This is not JSON"))]
            )
        )
        mock_openai_cls.return_value = llm
        from agent.reflector import validate

        results = [make_tool_result(tool="sql_query", success=True)]
        result = await validate("Test query", results)

        # Should return a valid dict with sensible defaults
        assert "confidence" in result
        assert "retry" in result

    @pytest.mark.asyncio
    @patch("agent.reflector.AsyncOpenAI")
    async def test_result_preview_truncated(self, mock_openai_cls):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='{"confidence": 0.85, "grounded": true, "issues": [], "retry": false}'
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        from agent.reflector import validate

        # Large result data
        big_data = {"rows": [["x" * 1000] for _ in range(50)], "columns": ["text"]}
        results = [make_tool_result(tool="sql_query", success=True, data=big_data)]

        result = await validate("Query", results)

        # Should not crash on large data
        assert result["confidence"] > 0
