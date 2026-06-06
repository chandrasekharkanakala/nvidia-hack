"""E2E tests for Light mode chat (real endpoints at localhost:8000)."""

import pytest
import httpx

BASE_URL = "http://localhost:8000"


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as c:
        yield c


@pytest.mark.e2e
class TestChatLightE2E:
    """End-to-end tests for Light mode: real request → real response."""

    @pytest.mark.asyncio
    async def test_simple_lookup_query(self, client):
        """Simple factual query should return an answer in < 2s."""
        response = await client.post("/api/chat", json={
            "content": "How many Underground journeys were there in Westminster in 2023?",
            "mode": "chat",
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["response"]) > 20
        assert "session_id" in data

    @pytest.mark.asyncio
    async def test_rag_based_query(self, client):
        """RAG query should return sourced information."""
        response = await client.post("/api/chat", json={
            "content": "What is the London congestion charge and how does it work?",
            "mode": "chat",
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["response"]) > 50
        assert "congestion" in data["response"].lower() or "charge" in data["response"].lower()

    @pytest.mark.asyncio
    async def test_weather_query(self, client):
        """Live weather query should return current data."""
        response = await client.post("/api/chat", json={
            "content": "What's the current weather in London?",
            "mode": "chat",
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["response"]) > 20

    @pytest.mark.asyncio
    async def test_light_mode_latency(self, client):
        """Light mode should respond within 2 seconds."""
        import time

        start = time.perf_counter()
        response = await client.post("/api/chat", json={
            "content": "What transport modes are available in London?",
            "mode": "chat",
        })
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < 2.0, f"Light mode took {elapsed:.2f}s, expected < 2s"

    @pytest.mark.asyncio
    async def test_session_continuity(self, client):
        """Multiple messages in same session should maintain context."""
        # First message
        r1 = await client.post("/api/chat", json={
            "content": "Tell me about bus usage in Camden",
            "mode": "chat",
        })
        session_id = r1.json()["session_id"]

        # Follow-up in same session
        r2 = await client.post("/api/chat", json={
            "content": "How does that compare to last year?",
            "mode": "chat",
            "session_id": session_id,
        })

        assert r2.status_code == 200
        assert r2.json()["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_sql_data_query(self, client):
        """SQL-backed query should return data-driven answer."""
        response = await client.post("/api/chat", json={
            "content": "What is the total number of bus journeys across all boroughs in Q1 2023?",
            "mode": "chat",
        })

        assert response.status_code == 200
        data = response.json()
        # Should reference numbers
        assert any(c.isdigit() for c in data["response"])

    @pytest.mark.asyncio
    async def test_tools_used_field_populated(self, client):
        """Response should indicate which tools were used."""
        response = await client.post("/api/chat", json={
            "content": "Query the database for air quality in Westminster",
            "mode": "chat",
        })

        assert response.status_code == 200
        data = response.json()
        assert "tools_used" in data
