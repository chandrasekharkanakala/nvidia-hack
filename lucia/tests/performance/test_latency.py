"""Performance tests: single-request latency per component."""

import pytest
import time
import httpx

BASE_URL = "http://localhost:8000"


@pytest.mark.performance
class TestLatencyPerComponent:
    """Measure and assert latency for individual components."""

    @pytest.mark.asyncio
    async def test_health_endpoint_latency(self, perf_client, perf_stats):
        """Health check should be nearly instant (< 50ms)."""
        for i in range(10):
            start = time.perf_counter()
            response = await perf_client.get("/health")
            elapsed_ms = (time.perf_counter() - start) * 1000

            perf_stats.record(f"health_{i}", elapsed_ms, success=response.status_code == 200)

        summary = perf_stats.summary
        assert summary["mean_ms"] < 50, f"Health avg {summary['mean_ms']:.1f}ms > 50ms"
        assert summary["max_ms"] < 200, f"Health max {summary['max_ms']:.1f}ms > 200ms"

    @pytest.mark.asyncio
    async def test_light_mode_e2e_latency(self, perf_client, perf_stats):
        """Light mode E2E should be < 2000ms."""
        queries = [
            "How many bus journeys in 2023?",
            "What is the air quality in Westminster?",
            "List transport modes available",
        ]

        for i, query in enumerate(queries):
            start = time.perf_counter()
            response = await perf_client.post("/chat", json={
                "content": query,
                "mode": "light",
            })
            elapsed_ms = (time.perf_counter() - start) * 1000

            perf_stats.record(f"light_{i}", elapsed_ms, success=response.status_code == 200)

        summary = perf_stats.summary
        assert summary["mean_ms"] < 2000, f"Light mode avg {summary['mean_ms']:.1f}ms > 2000ms"

    @pytest.mark.asyncio
    async def test_deep_mode_e2e_latency(self, perf_client, perf_stats):
        """Deep mode E2E should be < 15000ms."""
        start = time.perf_counter()
        response = await perf_client.post("/chat", json={
            "content": "Analyze transport trends and air quality correlation across all boroughs",
            "mode": "deep",
        })
        elapsed_ms = (time.perf_counter() - start) * 1000

        perf_stats.record("deep_analysis", elapsed_ms, success=response.status_code == 200)

        assert elapsed_ms < 15000, f"Deep mode took {elapsed_ms:.1f}ms > 15000ms"

    @pytest.mark.asyncio
    async def test_sql_query_latency(self, perf_client, perf_stats):
        """SQL-backed queries should resolve < 100ms (tool only)."""
        # This measures the full request, but SQL tool should be < 100ms
        start = time.perf_counter()
        response = await perf_client.post("/chat", json={
            "content": "SELECT COUNT(*) from transport data",
            "mode": "light",
        })
        elapsed_ms = (time.perf_counter() - start) * 1000

        perf_stats.record("sql_query", elapsed_ms, success=response.status_code == 200)

        # Full request includes LLM overhead, so we allow 2s total
        assert elapsed_ms < 2000, f"SQL query request took {elapsed_ms:.1f}ms"

    @pytest.mark.asyncio
    async def test_rag_retrieval_latency(self, perf_client, perf_stats):
        """RAG retrieval should be < 200ms (embedding + search)."""
        start = time.perf_counter()
        response = await perf_client.post("/chat", json={
            "content": "What are the congestion charge policies?",
            "mode": "light",
        })
        elapsed_ms = (time.perf_counter() - start) * 1000

        perf_stats.record("rag_search", elapsed_ms, success=response.status_code == 200)

        # Full request includes LLM synthesis
        assert elapsed_ms < 2000, f"RAG query request took {elapsed_ms:.1f}ms"

    @pytest.mark.asyncio
    async def test_vision_latency(self, perf_client, perf_stats):
        """Vision analysis should complete < 3000ms."""
        import base64

        # Minimal test image
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
            b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        image_b64 = base64.b64encode(png_bytes).decode()

        start = time.perf_counter()
        response = await perf_client.post("/chat", json={
            "content": "Describe this image",
            "mode": "light",
            "image": image_b64,
        })
        elapsed_ms = (time.perf_counter() - start) * 1000

        perf_stats.record("vision", elapsed_ms, success=response.status_code == 200)

        assert elapsed_ms < 3000, f"Vision took {elapsed_ms:.1f}ms > 3000ms"

    @pytest.mark.asyncio
    async def test_time_to_first_token_light(self, perf_client, perf_stats):
        """Time to first token in Light mode should be < 500ms."""
        # Use streaming endpoint to measure TTFT
        start = time.perf_counter()

        try:
            async with perf_client.stream("POST", "/chat/stream", json={
                "content": "Hello",
                "mode": "light",
            }) as response:
                async for chunk in response.aiter_bytes():
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    perf_stats.record("ttft_light", elapsed_ms, success=True)
                    break  # Only measure first chunk
        except Exception:
            # If streaming not available, measure full response
            response = await perf_client.post("/chat", json={
                "content": "Hello",
                "mode": "light",
            })
            elapsed_ms = (time.perf_counter() - start) * 1000
            perf_stats.record("ttft_light", elapsed_ms, success=response.status_code == 200)

        # TTFT target
        results = perf_stats.results
        if results:
            assert results[-1].elapsed_ms < 500, f"TTFT {results[-1].elapsed_ms:.1f}ms > 500ms"
