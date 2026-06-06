"""Metrics and GPU monitoring routes."""

import logging
import subprocess

import duckdb
from fastapi import APIRouter, Request

from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_metrics(request: Request):
    """Get aggregate stats from DuckDB metrics table."""
    try:
        db = getattr(request.app.state, "db", None)
        if db is None:
            db = duckdb.connect(settings.duckdb_path, read_only=True)
        result = db.execute("""
            SELECT
                COUNT(*) as total_requests,
                AVG(latency_ms) as avg_latency_ms,
                MAX(latency_ms) as max_latency_ms,
                MIN(latency_ms) as min_latency_ms,
                COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count,
                COUNT(DISTINCT endpoint) as unique_endpoints
            FROM metrics
        """).fetchone()

        columns = ["total_requests", "avg_latency_ms", "max_latency_ms", "min_latency_ms", "error_count", "unique_endpoints"]
        stats = dict(zip(columns, result)) if result else {}

        # Recent requests by endpoint
        top_endpoints = db.execute("""
            SELECT endpoint, COUNT(*) as count, AVG(latency_ms) as avg_latency
            FROM metrics
            GROUP BY endpoint
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()

        return {
            "summary": stats,
            "top_endpoints": [
                {"endpoint": row[0], "count": row[1], "avg_latency_ms": round(row[2], 2)}
                for row in top_endpoints
            ],
        }
    except Exception as e:
        logger.exception("Failed to get metrics")
        return {"summary": {}, "top_endpoints": [], "error": str(e)}


@router.get("/gpu")
async def get_gpu_metrics():
    """Get GPU metrics from nvidia-smi."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return {"gpus": [], "error": result.stderr.strip() or "nvidia-smi failed"}

        gpus = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6:
                gpus.append({
                    "index": int(parts[0]),
                    "name": parts[1],
                    "memory_used_mb": int(parts[2]),
                    "memory_total_mb": int(parts[3]),
                    "utilization_percent": int(parts[4]),
                    "temperature_c": int(parts[5]),
                })

        return {"gpus": gpus}

    except FileNotFoundError:
        return {"gpus": [], "error": "nvidia-smi not found"}
    except subprocess.TimeoutExpired:
        return {"gpus": [], "error": "nvidia-smi timed out"}
    except Exception as e:
        logger.exception("Failed to get GPU metrics")
        return {"gpus": [], "error": str(e)}
