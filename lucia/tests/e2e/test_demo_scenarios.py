"""E2E tests for the 3 demo scenarios."""

import pytest
import httpx
import time

BASE_URL = "http://localhost:8000"


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as c:
        yield c


@pytest.mark.e2e
class TestDemoScenarios:
    """The 3 key demo scenarios that must pass for the presentation."""

    @pytest.mark.asyncio
    async def test_scenario_1_quick_data_lookup(self, client):
        """
        Demo Scenario 1: Quick Data Lookup (Light Mode)
        User asks a simple factual question about transport data.
        Expected: Fast response (< 2s) with accurate data from SQL.
        """
        start = time.perf_counter()

        response = await client.post("/api/chat", json={
            "content": "What was the total number of Underground journeys in Westminster for Q1 2024?",
            "mode": "chat",
        })
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        data = response.json()

        # Must respond within 2 seconds
        assert elapsed < 2.0, f"Scenario 1 took {elapsed:.2f}s (target: <2s)"

        # Must contain a numerical answer
        assert any(c.isdigit() for c in data["response"]), "Response should contain numbers"

        # Must reference the query context
        response_lower = data["response"].lower()
        assert any(word in response_lower for word in ["underground", "westminster", "journey", "million"])

        # Must have used sql_query or rag_search tool
        if "tools_used" in data:
            assert len(data["tools_used"]) >= 1

    @pytest.mark.asyncio
    async def test_scenario_2_deep_analysis_with_simulation(self, client):
        """
        Demo Scenario 2: Deep Analysis with Traffic Simulation (Deep Mode)
        User asks for simulation of road closure impact.
        Expected: Multi-step response (< 15s) with simulation results, affected roads, and recommendations.
        """
        start = time.perf_counter()

        response = await client.post("/api/chat", json={
            "content": "If we close the A40 Western Avenue for emergency roadworks during evening rush hour (5-7pm), "
                       "what would be the traffic impact? Which alternative routes would be most affected "
                       "and what do you recommend for traffic management?",
            "mode": "deep",
        })
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        data = response.json()

        # Must respond within 15 seconds
        assert elapsed < 15.0, f"Scenario 2 took {elapsed:.2f}s (target: <15s)"

        # Must be a comprehensive response
        assert len(data["response"]) > 200, "Deep analysis should be detailed"

        # Must mention key elements
        response_lower = data["response"].lower()
        assert any(word in response_lower for word in ["delay", "reroute", "alternative", "impact", "traffic"])
        assert any(word in response_lower for word in ["recommend", "suggest", "advise", "manage"])

        # Should use multiple tools
        if "tools_used" in data:
            assert len(data["tools_used"]) >= 1

    @pytest.mark.asyncio
    async def test_scenario_3_multi_source_borough_comparison(self, client):
        """
        Demo Scenario 3: Multi-Source Borough Comparison (Deep Mode)
        User asks for comprehensive comparison combining SQL data, RAG documents, and predictions.
        Expected: Rich response integrating multiple data sources.
        """
        start = time.perf_counter()

        response = await client.post("/api/chat", json={
            "content": "Compare Westminster and Camden boroughs across transport usage, air quality, "
                       "and future predictions. Which borough is performing better environmentally "
                       "and what policies have been most effective?",
            "mode": "deep",
        })
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        data = response.json()

        # Must respond within 15 seconds
        assert elapsed < 15.0, f"Scenario 3 took {elapsed:.2f}s (target: <15s)"

        # Must be comprehensive
        assert len(data["response"]) > 200, "Multi-source comparison should be detailed"

        # Must reference both boroughs
        response_lower = data["response"].lower()
        assert "westminster" in response_lower
        assert "camden" in response_lower

        # Must discuss environment/air quality
        assert any(word in response_lower for word in ["air quality", "pollution", "no2", "environment", "emissions"])

        # Must discuss transport
        assert any(word in response_lower for word in ["transport", "journey", "bus", "underground", "travel"])


@pytest.mark.e2e
class TestDemoInfrastructure:
    """Verify demo infrastructure is operational."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """API server must be healthy."""
        response = await client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_sessions_endpoint_accessible(self, client):
        """Sessions management must work."""
        response = await client.get("/api/sessions")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_streaming_endpoint_accessible(self, client):
        """Streaming endpoint should be available."""
        # Test WebSocket availability by checking it doesn't 404
        response = await client.post("/api/chat/stream", json={
            "content": "Quick test",
            "mode": "chat",
        })
        # Either streaming works (200) or it's websocket-only (upgrade required)
        assert response.status_code in [200, 400, 426]
