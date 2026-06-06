"""Performance tests: concurrent load (5, 10, 20 users)."""

import pytest
import asyncio
import time
import httpx

from tests.performance.conftest import send_concurrent, Timer

BASE_URL = "http://localhost:8000"


@pytest.mark.performance
class TestThroughput:
    """Concurrent load tests to verify system handles multiple users."""

    @pytest.mark.asyncio
    async def test_5_concurrent_light_queries(self, perf_client, perf_stats):
        """5 concurrent Light mode requests should all complete < 5s."""
        queries = [
            "How many Underground journeys in 2023?",
            "What is the air quality in Camden?",
            "List bus routes in Southwark",
            "Total journeys by mode in Q1",
            "Compare Westminster and Hackney transport",
        ]

        requests = [
            {"method": "POST", "url": "/api/chat", "json": {"content": q, "mode": "chat"}}
            for q in queries
        ]

        results = await send_concurrent(perf_client, requests)

        for i, r in enumerate(results):
            perf_stats.record(f"concurrent_5_{i}", r["elapsed_ms"], success=r["success"])

        # All should succeed
        assert all(r["success"] for r in results), f"Some requests failed: {results}"
        # All should be under 5s
        assert all(r["elapsed_ms"] < 5000 for r in results), \
            f"Some requests > 5s: {[r['elapsed_ms'] for r in results]}"

    @pytest.mark.asyncio
    async def test_10_concurrent_light_queries(self, perf_client, perf_stats):
        """10 concurrent Light mode requests - measure degradation."""
        queries = [
            f"Query number {i}: What transport data is available?"
            for i in range(10)
        ]

        requests = [
            {"method": "POST", "url": "/api/chat", "json": {"content": q, "mode": "chat"}}
            for q in queries
        ]

        results = await send_concurrent(perf_client, requests)

        for i, r in enumerate(results):
            perf_stats.record(f"concurrent_10_{i}", r["elapsed_ms"], success=r["success"])

        success_rate = sum(1 for r in results if r["success"]) / len(results)
        assert success_rate >= 0.8, f"Success rate {success_rate:.0%} < 80%"

        times = [r["elapsed_ms"] for r in results if r["success"]]
        avg_ms = sum(times) / len(times) if times else 0
        assert avg_ms < 8000, f"Average latency {avg_ms:.1f}ms > 8000ms under 10 concurrent"

    @pytest.mark.asyncio
    async def test_20_concurrent_light_queries(self, perf_client, perf_stats):
        """20 concurrent requests - find degradation profile."""
        queries = [
            f"Concurrent test {i}: Show transport statistics"
            for i in range(20)
        ]

        requests = [
            {"method": "POST", "url": "/api/chat", "json": {"content": q, "mode": "chat"}}
            for q in queries
        ]

        results = await send_concurrent(perf_client, requests)

        for i, r in enumerate(results):
            perf_stats.record(f"concurrent_20_{i}", r["elapsed_ms"], success=r["success"])

        success_rate = sum(1 for r in results if r["success"]) / len(results)
        assert success_rate >= 0.7, f"Success rate {success_rate:.0%} < 70% under 20 concurrent"

        # Report p95 latency
        times = sorted([r["elapsed_ms"] for r in results if r["success"]])
        if times:
            p95 = times[int(len(times) * 0.95)]
            assert p95 < 15000, f"p95 latency {p95:.1f}ms > 15000ms under 20 concurrent"

    @pytest.mark.asyncio
    async def test_mixed_mode_concurrent(self, perf_client, perf_stats):
        """Mix of light and deep mode requests concurrently."""
        requests = [
            {"method": "POST", "url": "/api/chat", "json": {"content": "Quick lookup: bus stats", "mode": "chat"}},
            {"method": "POST", "url": "/api/chat", "json": {"content": "Quick lookup: air quality", "mode": "chat"}},
            {"method": "POST", "url": "/api/chat", "json": {"content": "Deep analysis: compare boroughs", "mode": "deep"}},
            {"method": "POST", "url": "/api/chat", "json": {"content": "Quick lookup: underground", "mode": "chat"}},
            {"method": "POST", "url": "/api/chat", "json": {"content": "Quick lookup: cycling", "mode": "chat"}},
        ]

        results = await send_concurrent(perf_client, requests)

        for i, r in enumerate(results):
            mode = "deep" if i == 2 else "light"
            perf_stats.record(f"mixed_{mode}_{i}", r["elapsed_ms"], success=r["success"])

        # Light requests should still be fast even alongside deep
        light_times = [results[i]["elapsed_ms"] for i in [0, 1, 3, 4] if results[i]["success"]]
        if light_times:
            avg_light = sum(light_times) / len(light_times)
            assert avg_light < 5000, f"Light queries degraded to {avg_light:.1f}ms under mixed load"

    @pytest.mark.asyncio
    async def test_health_under_load(self, perf_client, perf_stats):
        """Health endpoint should remain responsive under concurrent chat load."""
        # Fire off chat requests and health checks simultaneously
        requests = [
            {"method": "POST", "url": "/api/chat", "json": {"content": f"Query {i}", "mode": "chat"}}
            for i in range(5)
        ] + [
            {"method": "GET", "url": "/api/health"}
            for _ in range(5)
        ]

        results = await send_concurrent(perf_client, requests)

        # Health checks (last 5) should be fast
        health_results = results[5:]
        for i, r in enumerate(health_results):
            perf_stats.record(f"health_under_load_{i}", r["elapsed_ms"], success=r["success"])

        assert all(r["success"] for r in health_results), "Health checks failed under load"
        health_times = [r["elapsed_ms"] for r in health_results]
        assert max(health_times) < 1000, f"Health check took {max(health_times):.1f}ms under load"
