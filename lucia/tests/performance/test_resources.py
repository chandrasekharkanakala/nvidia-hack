"""Performance tests: GPU memory, CPU, disk usage under load."""

import pytest
import asyncio
import time
import psutil

from tests.performance.conftest import get_gpu_memory, send_concurrent, Timer

BASE_URL = "http://localhost:8000"


@pytest.mark.performance
class TestResourceUsage:
    """Monitor system resource usage under various load conditions."""

    @pytest.mark.asyncio
    async def test_gpu_memory_total_under_limit(self, perf_stats):
        """Total GPU memory usage should be < 100GB."""
        gpu_info = get_gpu_memory()

        if "error" in gpu_info:
            pytest.skip(f"GPU not available: {gpu_info['error']}")

        total_used_mb = sum(g["memory_used_mb"] for g in gpu_info["gpus"])
        total_used_gb = total_used_mb / 1024

        perf_stats.record("gpu_memory_total_gb", total_used_gb * 1000, success=total_used_gb < 100)

        assert total_used_gb < 100, f"GPU memory {total_used_gb:.1f}GB > 100GB limit"

    @pytest.mark.asyncio
    async def test_gpu_memory_per_model(self, perf_stats):
        """Individual GPU memory allocation should be reasonable."""
        gpu_info = get_gpu_memory()

        if "error" in gpu_info:
            pytest.skip(f"GPU not available: {gpu_info['error']}")

        for gpu in gpu_info["gpus"]:
            used_gb = gpu["memory_used_mb"] / 1024
            total_gb = gpu["memory_total_mb"] / 1024
            utilization = used_gb / total_gb if total_gb > 0 else 0

            perf_stats.record(
                f"gpu_{gpu['index']}_{gpu['name']}",
                gpu["memory_used_mb"],
                success=utilization < 0.95,
                total_mb=gpu["memory_total_mb"],
                utilization_pct=utilization * 100,
            )

            # No single GPU should be > 95% utilized at rest
            assert utilization < 0.95, \
                f"GPU {gpu['index']} ({gpu['name']}) at {utilization*100:.1f}% memory"

    @pytest.mark.asyncio
    async def test_cpu_usage_at_rest(self, perf_stats):
        """CPU usage at rest should be < 50%."""
        # Sample CPU over 2 seconds
        cpu_percent = psutil.cpu_percent(interval=2)

        perf_stats.record("cpu_at_rest", cpu_percent, success=cpu_percent < 50)

        assert cpu_percent < 50, f"CPU at rest: {cpu_percent}% > 50%"

    @pytest.mark.asyncio
    async def test_cpu_usage_under_load(self, perf_client, perf_stats):
        """CPU usage under 5 concurrent requests should be manageable."""
        # Start monitoring
        psutil.cpu_percent()  # Reset counter

        # Generate load
        requests = [
            {"method": "POST", "url": "/chat", "json": {"content": f"Query {i}", "mode": "light"}}
            for i in range(5)
        ]
        await send_concurrent(perf_client, requests)

        # Measure CPU after load
        cpu_percent = psutil.cpu_percent(interval=1)

        perf_stats.record("cpu_under_load_5", cpu_percent, success=cpu_percent < 90)

        # Should not max out CPU
        assert cpu_percent < 90, f"CPU under load: {cpu_percent}% > 90%"

    @pytest.mark.asyncio
    async def test_memory_usage_at_rest(self, perf_stats):
        """System memory usage should be reasonable."""
        memory = psutil.virtual_memory()
        used_gb = memory.used / (1024 ** 3)
        total_gb = memory.total / (1024 ** 3)
        percent = memory.percent

        perf_stats.record("ram_usage_percent", percent, success=percent < 90)

        assert percent < 90, f"RAM usage {percent}% > 90% ({used_gb:.1f}/{total_gb:.1f} GB)"

    @pytest.mark.asyncio
    async def test_memory_no_leak_under_repeated_requests(self, perf_client, perf_stats):
        """Memory should not grow significantly after repeated requests."""
        process = psutil.Process()

        # Baseline memory
        baseline_mb = process.memory_info().rss / (1024 ** 2)

        # Send 20 requests sequentially
        for i in range(20):
            await perf_client.post("/chat", json={
                "content": f"Memory test query {i}",
                "mode": "light",
            })

        # Allow GC
        await asyncio.sleep(1)

        # Final memory
        final_mb = process.memory_info().rss / (1024 ** 2)
        growth_mb = final_mb - baseline_mb

        perf_stats.record("memory_growth_20_requests", growth_mb, success=growth_mb < 500)

        # Should not grow more than 500MB for 20 requests
        assert growth_mb < 500, f"Memory grew {growth_mb:.1f}MB after 20 requests"

    @pytest.mark.asyncio
    async def test_gpu_memory_under_load(self, perf_client, perf_stats):
        """GPU memory should not spike excessively under concurrent load."""
        gpu_before = get_gpu_memory()
        if "error" in gpu_before:
            pytest.skip("GPU not available")

        before_total = sum(g["memory_used_mb"] for g in gpu_before["gpus"])

        # Generate load
        requests = [
            {"method": "POST", "url": "/chat", "json": {"content": f"GPU load test {i}", "mode": "light"}}
            for i in range(10)
        ]
        await send_concurrent(perf_client, requests)

        gpu_after = get_gpu_memory()
        after_total = sum(g["memory_used_mb"] for g in gpu_after.get("gpus", []))
        spike_mb = after_total - before_total

        perf_stats.record("gpu_memory_spike_mb", spike_mb, success=spike_mb < 10000)

        # Should not spike more than 10GB under load
        assert spike_mb < 10000, f"GPU memory spiked {spike_mb}MB under 10 concurrent requests"

    @pytest.mark.asyncio
    async def test_disk_usage(self, perf_stats):
        """Disk usage for data directory should be reasonable."""
        disk = psutil.disk_usage("/")
        percent = disk.percent

        perf_stats.record("disk_usage_percent", percent, success=percent < 90)

        assert percent < 90, f"Disk usage {percent}% > 90%"
