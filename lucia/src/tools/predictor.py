"""Predictor tool — time-series forecasting using historical DuckDB data."""

import logging
from datetime import datetime, timezone

import duckdb
import numpy as np

from config.settings import settings

logger = logging.getLogger(__name__)


def _seasonal_decompose(values: list[float], period: int = 24) -> dict:
    """Simple seasonal decomposition for prediction."""
    arr = np.array(values, dtype=np.float64)

    if len(arr) < period * 2:
        # Not enough data for seasonal decomposition, use simple moving average
        trend = np.convolve(arr, np.ones(min(7, len(arr))) / min(7, len(arr)), mode="same")
        seasonal = np.zeros_like(arr)
    else:
        # Compute trend with moving average
        kernel_size = min(period, len(arr) // 2)
        trend = np.convolve(arr, np.ones(kernel_size) / kernel_size, mode="same")

        # Compute seasonal component
        detrended = arr - trend
        seasonal = np.zeros(period)
        for i in range(period):
            indices = list(range(i, len(detrended), period))
            seasonal[i] = np.mean(detrended[indices])

    return {"trend": trend, "seasonal": seasonal, "period": period}


async def execute(metric: str, road: str, horizon_hours: int = 24) -> dict:
    """Predict future values for a metric on a given road."""
    try:
        db_path = settings.duckdb_path if hasattr(settings, "duckdb_path") else "data/lucia.duckdb"
        conn = duckdb.connect(db_path, read_only=True)

        try:
            # Query historical data
            query = f"""
                SELECT value, timestamp
                FROM congestion_charge
                WHERE road = ? OR location = ?
                ORDER BY timestamp DESC
                LIMIT 720
            """
            try:
                result = conn.execute(query, [road, road])
                rows = result.fetchall()
            except duckdb.Error:
                # Fallback: try generic metrics table
                query = """
                    SELECT value, timestamp
                    FROM metrics
                    WHERE metric_name = ? AND location = ?
                    ORDER BY timestamp DESC
                    LIMIT 720
                """
                try:
                    result = conn.execute(query, [metric, road])
                    rows = result.fetchall()
                except duckdb.Error:
                    rows = []
        finally:
            conn.close()

        if not rows:
            # Generate synthetic predictions when no historical data available
            predictions = []
            base_value = 50.0
            for h in range(horizon_hours):
                hour = (datetime.now(timezone.utc).hour + h) % 24
                # Simulate daily pattern
                if 7 <= hour <= 9 or 16 <= hour <= 19:
                    value = base_value * 1.5 + np.random.normal(0, 5)
                else:
                    value = base_value * 0.7 + np.random.normal(0, 3)
                predictions.append({"hour_offset": h, "value": round(float(value), 2)})

            return {
                "target": metric,
                "road": road,
                "horizon": horizon_hours,
                "predictions": predictions,
                "confidence": 0.5,
                "note": "Synthetic predictions — no historical data available.",
            }

        # Extract values and decompose
        values = [float(row[0]) for row in reversed(rows)]
        decomp = _seasonal_decompose(values)

        # Generate predictions
        trend_slope = (decomp["trend"][-1] - decomp["trend"][0]) / max(len(decomp["trend"]) - 1, 1)
        last_trend = decomp["trend"][-1]

        predictions = []
        for h in range(horizon_hours):
            trend_val = last_trend + trend_slope * (h + 1)
            seasonal_val = decomp["seasonal"][h % decomp["period"]]
            predicted = trend_val + seasonal_val
            predictions.append({"hour_offset": h, "value": round(float(predicted), 2)})

        # Confidence based on data quantity
        confidence = min(0.95, len(values) / 720.0)

        return {
            "target": metric,
            "road": road,
            "horizon": horizon_hours,
            "predictions": predictions,
            "confidence": round(confidence, 2),
        }

    except Exception as e:
        logger.exception("Predictor failed")
        return {
            "target": metric,
            "road": road,
            "horizon": horizon_hours,
            "predictions": [],
            "confidence": 0.0,
            "error": str(e),
        }
