"""Performance test fixtures and utilities."""

import time
import asyncio
import subprocess
import json
from dataclasses import dataclass, field
from typing import Optional

import pytest
import httpx


def pytest_collection_modifyitems(config, items):
    """Skip performance tests if server is not running."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.connect(("localhost", 8000))
        sock.close()
    except (ConnectionRefusedError, OSError):
        sock.close()
        skip = pytest.mark.skip(reason="FastAPI server not running on localhost:8000")
        for item in items:
            if "performance" in str(item.fspath):
                item.add_marker(skip)


class Timer:
    """Context manager for timing code blocks."""

    def __init__(self):
        self.start_time: float = 0
        self.end_time: float = 0
        self.elapsed_ms: float = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end_time = time.perf_counter()
        self.elapsed_ms = (self.end_time - self.start_time) * 1000


@dataclass
class PerfResult:
    name: str
    elapsed_ms: float
    success: bool
    metadata: dict = field(default_factory=dict)


@dataclass
class PerfStats:
    """Records performance results and generates reports."""

    results: list[PerfResult] = field(default_factory=list)

    def record(self, name: str, elapsed_ms: float, success: bool = True, **metadata):
        self.results.append(PerfResult(name=name, elapsed_ms=elapsed_ms, success=success, metadata=metadata))

    @property
    def summary(self) -> dict:
        if not self.results:
            return {}
        times = [r.elapsed_ms for r in self.results]
        return {
            "count": len(self.results),
            "mean_ms": sum(times) / len(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "p95_ms": sorted(times)[int(len(times) * 0.95)] if len(times) >= 20 else max(times),
            "success_rate": sum(1 for r in self.results if r.success) / len(self.results),
        }

    def markdown_report(self) -> str:
        """Generate a markdown table of results."""
        lines = [
            "| Test | Duration (ms) | Status |",
            "|------|--------------|--------|",
        ]
        for r in self.results:
            status = "✓" if r.success else "✗"
            lines.append(f"| {r.name} | {r.elapsed_ms:.1f} | {status} |")

        s = self.summary
        if s:
            lines.append("")
            lines.append(f"**Summary**: {s['count']} tests | "
                         f"Mean: {s['mean_ms']:.1f}ms | "
                         f"Min: {s['min_ms']:.1f}ms | "
                         f"Max: {s['max_ms']:.1f}ms | "
                         f"Success: {s['success_rate']*100:.0f}%")
        return "\n".join(lines)


def get_gpu_memory() -> dict:
    """Query GPU memory from nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,memory.free",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return {"error": "nvidia-smi failed", "stderr": result.stderr}

        gpus = []
        for line in result.stdout.strip().split("\n"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 5:
                gpus.append({
                    "index": int(parts[0]),
                    "name": parts[1],
                    "memory_used_mb": int(parts[2]),
                    "memory_total_mb": int(parts[3]),
                    "memory_free_mb": int(parts[4]),
                })
        return {"gpus": gpus}
    except FileNotFoundError:
        return {"error": "nvidia-smi not found"}
    except subprocess.TimeoutExpired:
        return {"error": "nvidia-smi timed out"}


@pytest.fixture
def perf_client() -> httpx.AsyncClient:
    """httpx async client pointing at localhost:8000."""
    return httpx.AsyncClient(base_url="http://localhost:8000", timeout=60.0)


@pytest.fixture
def perf_stats() -> PerfStats:
    """Fresh PerfStats instance for each test."""
    return PerfStats()


async def send_concurrent(
    client: httpx.AsyncClient,
    requests: list[dict],
) -> list[dict]:
    """Send multiple requests concurrently and return timing results.

    Each request dict should have: method, url, and optionally json/data.
    Returns list of dicts with: status_code, elapsed_ms, success, response_size.
    """

    async def _send_one(req: dict) -> dict:
        method = req.get("method", "POST").upper()
        url = req.get("url", "/")
        body = req.get("json")

        timer = Timer()
        try:
            with timer:
                if method == "POST":
                    resp = await client.post(url, json=body)
                elif method == "GET":
                    resp = await client.get(url)
                else:
                    resp = await client.request(method, url, json=body)

            return {
                "status_code": resp.status_code,
                "elapsed_ms": timer.elapsed_ms,
                "success": 200 <= resp.status_code < 400,
                "response_size": len(resp.content),
            }
        except Exception as e:
            return {
                "status_code": 0,
                "elapsed_ms": timer.elapsed_ms,
                "success": False,
                "error": str(e),
                "response_size": 0,
            }

    results = await asyncio.gather(*[_send_one(r) for r in requests])
    return list(results)
