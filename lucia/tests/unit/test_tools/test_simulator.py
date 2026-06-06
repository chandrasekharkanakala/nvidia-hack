"""Unit tests for the simulator tool."""

import pytest
from unittest.mock import patch, MagicMock


class TestSimulatorExecute:
    """Tests for simulator.execute() traffic simulation."""

    @pytest.mark.asyncio
    async def test_simulates_road_closure(self):
        from tools.simulator import execute

        result = await execute(road="A40", duration_hours=2.0, time_of_day="17:00")

        assert "affected_roads" in result
        assert "avg_delay_minutes" in result
        assert "total_rerouted" in result
        assert "recommendation" in result

    @pytest.mark.asyncio
    async def test_affected_roads_not_empty(self):
        from tools.simulator import execute

        result = await execute(road="A40", duration_hours=1.0, time_of_day="08:00")

        assert len(result["affected_roads"]) > 0

    @pytest.mark.asyncio
    async def test_peak_hour_higher_delay(self):
        from tools.simulator import execute

        peak_result = await execute(road="A40", duration_hours=2.0, time_of_day="08:00")
        offpeak_result = await execute(road="A40", duration_hours=2.0, time_of_day="03:00")

        # Peak hours should cause more delay
        assert peak_result["avg_delay_minutes"] >= offpeak_result["avg_delay_minutes"]

    @pytest.mark.asyncio
    async def test_longer_duration_more_rerouted(self):
        from tools.simulator import execute

        short = await execute(road="A40", duration_hours=1.0, time_of_day="12:00")
        long = await execute(road="A40", duration_hours=5.0, time_of_day="12:00")

        # More hours → more total rerouted vehicles
        assert long["total_rerouted"] >= short["total_rerouted"]

    @pytest.mark.asyncio
    async def test_unknown_road_handled(self):
        from tools.simulator import execute

        result = await execute(road="NONEXISTENT_ROAD", duration_hours=1.0, time_of_day="12:00")

        # Should handle gracefully (either error or empty results)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_recommendation_is_string(self):
        from tools.simulator import execute

        result = await execute(road="M25", duration_hours=3.0, time_of_day="17:30")

        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 0

    @pytest.mark.asyncio
    async def test_delay_is_positive(self):
        from tools.simulator import execute

        result = await execute(road="A1", duration_hours=2.0, time_of_day="09:00")

        assert result["avg_delay_minutes"] >= 0

    @pytest.mark.asyncio
    async def test_rerouted_is_realistic(self):
        from tools.simulator import execute

        result = await execute(road="A40", duration_hours=2.0, time_of_day="17:00")

        # Should be between 200-1500 per path × number of paths
        assert result["total_rerouted"] >= 0
        assert result["total_rerouted"] < 100000  # sanity check
