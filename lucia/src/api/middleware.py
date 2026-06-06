"""Request logging and metrics middleware."""

import time
import logging

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with structlog and record latency in DuckDB."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                error=str(e),
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            duration_ms=round(duration_ms, 2),
            status_code=response.status_code,
        )

        # Record metrics in DuckDB
        try:
            db = request.app.state.db
            db.execute(
                "INSERT INTO metrics (endpoint, method, status_code, latency_ms) VALUES (?, ?, ?, ?)",
                [request.url.path, request.method, response.status_code, duration_ms],
            )
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to record metric: {e}")

        return response
