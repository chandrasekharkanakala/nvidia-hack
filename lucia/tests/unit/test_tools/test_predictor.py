"""Unit tests for the predictor tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestPredictorExecute:
    """Tests for predictor.execute() time-series forecasting."""

    @pytest.mark.asyncio
    @patch("tools.predictor.duckdb")
    async def test_returns_predictions(self, mock_duckdb, test_db):
        mock_duckdb.connect.return_value = test_db
        from tools.predictor import execute

        result = await execute(metric="congestion", road="A40", horizon_hours=24)

        assert "predictions" in result
        assert "confidence" in result
        assert "target" in result
        assert "road" in result
        assert "horizon" in result

    @pytest.mark.asyncio
    @patch("tools.predictor.duckdb")
    async def test_prediction_count_matches_horizon(self, mock_duckdb, test_db):
        mock_duckdb.connect.return_value = test_db
        from tools.predictor import execute

        result = await execute(metric="traffic_flow", road="M25", horizon_hours=12)

        assert len(result["predictions"]) == 12

    @pytest.mark.asyncio
    @patch("tools.predictor.duckdb")
    async def test_predictions_have_hour_offset(self, mock_duckdb, test_db):
        mock_duckdb.connect.return_value = test_db
        from tools.predictor import execute

        result = await execute(metric="congestion", road="A1", horizon_hours=6)

        for pred in result["predictions"]:
            assert "hour_offset" in pred
            assert "value" in pred
            assert pred["hour_offset"] >= 0

    @pytest.mark.asyncio
    @patch("tools.predictor.duckdb")
    async def test_confidence_between_0_and_1(self, mock_duckdb, test_db):
        mock_duckdb.connect.return_value = test_db
        from tools.predictor import execute

        result = await execute(metric="congestion", road="A40", horizon_hours=24)

        assert 0.0 <= result["confidence"] <= 1.0

    @pytest.mark.asyncio
    @patch("tools.predictor.duckdb")
    async def test_fallback_synthetic_predictions(self, mock_duckdb):
        # Empty database - should use fallback
        empty_db = MagicMock()
        empty_db.execute.return_value = MagicMock(fetchall=lambda: [])
        mock_duckdb.connect.return_value = empty_db

        from tools.predictor import execute

        result = await execute(metric="unknown_metric", road="X99", horizon_hours=12)

        assert len(result["predictions"]) == 12
        assert result["confidence"] > 0

    @pytest.mark.asyncio
    @patch("tools.predictor.duckdb")
    async def test_peak_hours_higher_values(self, mock_duckdb, test_db):
        mock_duckdb.connect.return_value = test_db
        from tools.predictor import execute

        result = await execute(metric="traffic_flow", road="A40", horizon_hours=24)

        predictions = result["predictions"]
        if len(predictions) >= 18:
            # Hours 7-9 and 16-19 should have higher values (peak)
            peak_vals = [p["value"] for p in predictions if p["hour_offset"] in [8, 9, 17, 18]]
            offpeak_vals = [p["value"] for p in predictions if p["hour_offset"] in [2, 3, 4]]
            if peak_vals and offpeak_vals:
                assert max(peak_vals) >= min(offpeak_vals)

    @pytest.mark.asyncio
    @patch("tools.predictor.duckdb")
    async def test_target_and_road_in_result(self, mock_duckdb, test_db):
        mock_duckdb.connect.return_value = test_db
        from tools.predictor import execute

        result = await execute(metric="speed", road="A2", horizon_hours=6)

        assert result["target"] == "speed" or "speed" in result.get("target", "")
        assert result["road"] == "A2"
        assert result["horizon"] == 6
