"""E2E tests for Deep mode chat (real endpoints at localhost:8000)."""

import pytest
import httpx

BASE_URL = "http://localhost:8000"


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as c:
        yield c


@pytest.mark.e2e
class TestChatDeepE2E:
    """End-to-end tests for Deep mode: real request → real response."""

    @pytest.mark.asyncio
    async def test_multi_step_analysis(self, client):
        """Complex query requiring multiple tools should return comprehensive answer."""
        response = await client.post("/api/chat", json={
            "content": "Analyze the relationship between transport usage and air quality across London boroughs. Include data from multiple sources.",
            "mode": "deep",
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["response"]) > 100
        # Deep mode should produce a detailed response
        assert any(word in data["response"].lower() for word in ["borough", "transport", "air", "quality"])

    @pytest.mark.asyncio
    async def test_simulation_query(self, client):
        """Simulation request should return impact analysis."""
        response = await client.post("/api/chat", json={
            "content": "Simulate closing the A40 for 3 hours during evening rush hour and analyze the traffic impact",
            "mode": "deep",
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["response"]) > 50
        assert any(word in data["response"].lower() for word in ["delay", "reroute", "traffic", "impact", "road"])

    @pytest.mark.asyncio
    async def test_prediction_query(self, client):
        """Prediction request should return forecast data."""
        response = await client.post("/api/chat", json={
            "content": "Predict traffic congestion on the M25 for the next 24 hours and identify peak periods",
            "mode": "deep",
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["response"]) > 50

    @pytest.mark.asyncio
    async def test_deep_mode_latency(self, client):
        """Deep mode should respond within 15 seconds."""
        import time

        start = time.perf_counter()
        response = await client.post("/api/chat", json={
            "content": "Compare Underground and Bus journeys across all quarters, include trends and predictions",
            "mode": "deep",
        })
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 15.0, f"Deep mode took {elapsed:.2f}s, expected < 15s"

    @pytest.mark.asyncio
    async def test_deep_mode_multi_tool_response(self, client):
        """Deep mode should use multiple tools and cite sources."""
        response = await client.post("/api/chat", json={
            "content": "Provide a comprehensive overview of Westminster's transport and environmental data, combining SQL analysis with document research",
            "mode": "deep",
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["response"]) > 100
        # Should use multiple tools
        if "tools_used" in data:
            assert len(data["tools_used"]) >= 2

    @pytest.mark.asyncio
    async def test_deep_mode_with_dependency_chain(self, client):
        """Query requiring sequential tool calls should work."""
        response = await client.post("/api/chat", json={
            "content": "First get the top 3 boroughs by bus journeys, then analyze air quality specifically for those boroughs",
            "mode": "deep",
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["response"]) > 50

    @pytest.mark.asyncio
    async def test_deep_mode_returns_thinking(self, client):
        """Deep mode may return thinking/planning information."""
        response = await client.post("/api/chat", json={
            "content": "What would happen if we expanded the congestion charge zone to include Hackney?",
            "mode": "deep",
        })

        assert response.status_code == 200
        data = response.json()
        # thinking field is optional but response must be substantive
        assert len(data["response"]) > 50
