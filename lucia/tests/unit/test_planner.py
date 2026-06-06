"""Unit tests for the Planner (query decomposition)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.factories import make_plan_step


@pytest.fixture
def planner_llm_response():
    """LLM that returns a valid multi-step plan."""
    plan_json = """[
        {"tool": "sql_query", "params": {"query": "SELECT borough, AVG(concentration) FROM air_quality GROUP BY borough"}, "depends_on": null},
        {"tool": "rag_search", "params": {"query": "London air quality policy changes 2023"}, "depends_on": null},
        {"tool": "sql_query", "params": {"query": "SELECT mode, SUM(journeys_millions) FROM transport_journeys GROUP BY mode"}, "depends_on": 0}
    ]"""
    mock = AsyncMock()
    mock.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content=plan_json))]
        )
    )
    return mock


class TestPlannerCreatePlan:
    """Tests for planner.create_plan() query decomposition."""

    @pytest.mark.asyncio
    @patch("agent.planner.AsyncOpenAI")
    async def test_creates_multi_step_plan(self, mock_openai_cls, planner_llm_response):
        mock_openai_cls.return_value = planner_llm_response
        from agent.planner import create_plan

        steps = await create_plan(
            "Compare air quality and transport usage across boroughs",
            intent="analysis",
            history=[],
        )

        assert isinstance(steps, list)
        assert len(steps) == 3
        assert steps[0]["tool"] == "sql_query"
        assert steps[1]["tool"] == "rag_search"

    @pytest.mark.asyncio
    @patch("agent.planner.AsyncOpenAI")
    async def test_plan_steps_have_required_keys(self, mock_openai_cls, planner_llm_response):
        mock_openai_cls.return_value = planner_llm_response
        from agent.planner import create_plan

        steps = await create_plan("Analyze trends", intent="analysis", history=[])

        for step in steps:
            assert "tool" in step
            assert "params" in step
            assert "depends_on" in step

    @pytest.mark.asyncio
    @patch("agent.planner.AsyncOpenAI")
    async def test_dependency_chain_preserved(self, mock_openai_cls, planner_llm_response):
        mock_openai_cls.return_value = planner_llm_response
        from agent.planner import create_plan

        steps = await create_plan("Complex query", intent="analysis", history=[])

        # Step 2 depends on step 0
        assert steps[2]["depends_on"] == 0 or steps[2]["depends_on"] == [0]

    @pytest.mark.asyncio
    @patch("agent.planner.AsyncOpenAI")
    async def test_fallback_on_invalid_json(self, mock_openai_cls):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content="I can't create a plan for that"))]
            )
        )
        mock_openai_cls.return_value = llm
        from agent.planner import create_plan

        steps = await create_plan("Something", intent="lookup", history=[])

        # Should fallback to single sql_query
        assert isinstance(steps, list)
        assert len(steps) >= 1
        assert steps[0]["tool"] == "sql_query"

    @pytest.mark.asyncio
    @patch("agent.planner.AsyncOpenAI")
    async def test_max_steps_limit(self, mock_openai_cls):
        # Return 10 steps
        big_plan = str([{"tool": "sql_query", "params": {"query": f"SELECT {i}"}, "depends_on": None} for i in range(10)])
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content=big_plan))]
            )
        )
        mock_openai_cls.return_value = llm
        from agent.planner import create_plan

        steps = await create_plan("Huge query", intent="analysis", history=[])

        # Should be capped at max_steps (typically 5)
        assert len(steps) <= 5

    @pytest.mark.asyncio
    @patch("agent.planner.AsyncOpenAI")
    async def test_single_step_plan(self, mock_openai_cls):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='[{"tool": "sql_query", "params": {"query": "SELECT COUNT(*) FROM transport_journeys"}, "depends_on": null}]'
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        from agent.planner import create_plan

        steps = await create_plan("How many journeys total?", intent="lookup", history=[])

        assert len(steps) == 1
        assert steps[0]["tool"] == "sql_query"

    @pytest.mark.asyncio
    @patch("agent.planner.AsyncOpenAI")
    async def test_llm_exception_returns_fallback(self, mock_openai_cls):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(side_effect=Exception("LLM timeout"))
        mock_openai_cls.return_value = llm
        from agent.planner import create_plan

        steps = await create_plan("Query", intent="lookup", history=[])

        assert isinstance(steps, list)
        assert len(steps) >= 1
