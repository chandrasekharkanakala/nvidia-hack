"""Performance tests: find breaking point (ramp until failure)."""

import pytest
import asyncio
import time
import httpx

from tests.performance.conftest import send_concurrent, Timer, PerfStats

BASE_URL = "http://localhost:8000"


@pytest.mark.performance
class TestStress:
    """Stress tests to find the system's breaking point."""

    @pytest.mark.asyncio
    async def test_ramp_until_degradation(self, perf_client, perf_stats):
        """Ramp concurrent users until latency exceeds threshold."""
        levels = [5, 10, 15, 20, 30, 50]
        degradation_level = None
        target_p95_ms = 10000  # 10s threshold

        for n_users in levels:
            requests = [
                {"method": "POST", "url": "/chat", "json": {
                    "content": f"Stress test user {i}: transport data query",
                    "mode": "light",
                }}
                for i in range(n_users)
            ]

            results = await send_concurrent(perf_client, requests)

            success_count = sum(1 for r in results if r["success"])
            success_rate = success_count / len(results)
            times = sorted([r["elapsed_ms"] for r in results if r["success"]])
            p95 = times[int(len(times) * 0.95)] if times else float("inf")

            perf_stats.record(
                f"stress_{n_users}_users",
                p95,
                success=success_rate >= 0.8 and p95 < target_p95_ms,
                n_users=n_users,
                success_rate=success_rate,
                p95_ms=p95,
            )

            if success_rate < 0.8 or p95 > target_p95_ms:
                degradation_level = n_users
                break

            # Cool down between levels
            await asyncio.sleep(2)

        # System should handle at least 5 concurrent users
        if degradation_level:
            assert degradation_level > 5, \
                f"System degraded at {degradation_level} users (minimum: 5)"

    @pytest.mark.asyncio
    async def test_sustained_load(self, perf_client, perf_stats):
        """5 concurrent users sustained for 30 seconds."""
        duration_s = 30
        concurrent = 5
        start = time.perf_counter()
        total_requests = 0
        failures = 0

        while (time.perf_counter() - start) < duration_s:
            requests = [
                {"method": "POST", "url": "/chat", "json": {
                    "content": f"Sustained load test {total_requests + i}",
                    "mode": "light",
                }}
                for i in range(concurrent)
            ]

            results = await send_concurrent(perf_client, requests)
            total_requests += len(results)
            failures += sum(1 for r in results if not r["success"])

            for i, r in enumerate(results):
                perf_stats.record(
                    f"sustained_{total_requests - len(results) + i}",
                    r["elapsed_ms"],
                    success=r["success"],
                )

        total_time = time.perf_counter() - start
        throughput = total_requests / total_time
        error_rate = failures / total_requests if total_requests > 0 else 1.0

        assert error_rate < 0.1, \
            f"Error rate {error_rate*100:.1f}% > 10% during sustained load"
        assert throughput > 0.5, \
            f"Throughput {throughput:.2f} req/s too low during sustained load"

    @pytest.mark.asyncio
    async def test_burst_recovery(self, perf_client, perf_stats):
        """System should recover after a burst of requests."""
        # Baseline latency
        start = time.perf_counter()
        baseline_resp = await perf_client.post("/chat", json={
            "content": "Baseline query",
            "mode": "light",
        })
        baseline_ms = (time.perf_counter() - start) * 1000

        # Burst: 20 concurrent requests
        burst_requests = [
            {"method": "POST", "url": "/chat", "json": {
                "content": f"Burst query {i}",
                "mode": "light",
            }}
            for i in range(20)
        ]
        await send_concurrent(perf_client, burst_requests)

        # Recovery period
        await asyncio.sleep(3)

        # Post-burst latency
        start = time.perf_counter()
        recovery_resp = await perf_client.post("/chat", json={
            "content": "Recovery query",
            "mode": "light",
        })
        recovery_ms = (time.perf_counter() - start) * 1000

        perf_stats.record("burst_baseline", baseline_ms, success=baseline_resp.status_code == 200)
        perf_stats.record("burst_recovery", recovery_ms, success=recovery_resp.status_code == 200)

        # Recovery latency should not be more than 3x baseline
        if baseline_ms > 0:
            degradation_factor = recovery_ms / baseline_ms
            assert degradation_factor < 3.0, \
                f"Post-burst latency {recovery_ms:.0f}ms is {degradation_factor:.1f}x baseline {baseline_ms:.0f}ms"

    @pytest.mark.asyncio
    async def test_deep_mode_under_concurrent_light(self, perf_client, perf_stats):
        """Deep mode should still work while light mode is under load."""
        # Send 10 light + 1 deep concurrently
        requests = [
            {"method": "POST", "url": "/chat", "json": {
                "content": f"Light stress {i}",
                "mode": "light",
            }}
            for i in range(10)
        ] + [
            {"method": "POST", "url": "/chat", "json": {
                "content": "Deep analysis: compare all borough transport data with air quality trends",
                "mode": "deep",
            }}
        ]

        results = await send_concurrent(perf_client, requests)

        deep_result = results[-1]
        perf_stats.record("deep_under_light_load", deep_result["elapsed_ms"], success=deep_result["success"])

        # Deep mode should still succeed
        assert deep_result["success"], "Deep mode failed under concurrent light load"
        assert deep_result["elapsed_ms"] < 20000, \
            f"Deep mode took {deep_result['elapsed_ms']:.0f}ms under load (limit: 20s)"

    @pytest.mark.asyncio
    async def test_error_rate_at_capacity(self, perf_client, perf_stats):
        """Measure error rate at high concurrency."""
        n_requests = 30
        requests = [
            {"method": "POST", "url": "/chat", "json": {
                "content": f"Capacity test {i}",
                "mode": "light",
            }}
            for i in range(n_requests)
        ]

        results = await send_concurrent(perf_client, requests)

        successes = sum(1 for r in results if r["success"])
        failures = n_requests - successes
        error_rate = failures / n_requests

        perf_stats.record(
            "error_rate_at_30",
            error_rate * 100,
            success=error_rate < 0.2,
            total=n_requests,
            successes=successes,
            failures=failures,
        )

        # Should not have > 20% error rate
        assert error_rate < 0.2, \
            f"Error rate {error_rate*100:.1f}% at 30 concurrent ({failures} failures)"
