"""Integration tests for FastAPI endpoints (httpx ASGI client)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.factories import make_session_id


class TestHealthEndpoint:
    """Tests for GET /health."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, test_client):
        response = await test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "lucia"


class TestChatEndpoint:
    """Tests for POST /chat."""

    @pytest.mark.asyncio
    @patch("agent.process_message")
    async def test_chat_returns_response(self, mock_process, test_client):
        mock_process.return_value = {
            "content": "The Underground carries 320M journeys per quarter.",
            "mode": "light",
            "metrics": {"total_ms": 150, "intent": "lookup"},
            "tool_calls": ["sql_query"],
        }

        response = await test_client.post("/chat", json={
            "content": "How many Underground journeys?",
            "mode": "chat",
            "session_id": make_session_id(),
        })

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data

    @pytest.mark.asyncio
    @patch("agent.process_message")
    async def test_chat_creates_session_if_none(self, mock_process, test_client):
        mock_process.return_value = {
            "content": "Answer",
            "mode": "light",
            "metrics": {},
            "tool_calls": [],
        }

        response = await test_client.post("/chat", json={
            "content": "Hello",
            "mode": "chat",
        })

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    @pytest.mark.asyncio
    async def test_chat_validates_empty_content(self, test_client):
        response = await test_client.post("/chat", json={
            "content": "",
            "mode": "chat",
        })

        # Should reject empty content
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    @patch("agent.process_message")
    async def test_chat_returns_tools_used(self, mock_process, test_client):
        mock_process.return_value = {
            "content": "Data shows...",
            "mode": "deep",
            "metrics": {"total_ms": 5000},
            "tool_calls": ["sql_query", "rag_search", "sql_query"],
        }

        response = await test_client.post("/chat", json={
            "content": "Complex analysis",
            "mode": "deep",
            "session_id": make_session_id(),
        })

        data = response.json()
        assert "tools_used" in data
        assert len(data["tools_used"]) > 0


class TestSessionsEndpoint:
    """Tests for /sessions/ endpoints."""

    @pytest.mark.asyncio
    @patch("agent.memory.list_sessions")
    async def test_list_sessions(self, mock_list, test_client):
        mock_list.return_value = [
            {"id": "abc-123", "title": "Transport query", "message_count": 4},
            {"id": "def-456", "title": "Air quality analysis", "message_count": 8},
        ]

        response = await test_client.get("/sessions/")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert len(data["sessions"]) == 2

    @pytest.mark.asyncio
    @patch("agent.memory.load_history")
    async def test_get_session_messages(self, mock_load, test_client):
        session_id = make_session_id()
        mock_load.return_value = [
            {"role": "user", "content": "Hello", "mode": "light"},
            {"role": "assistant", "content": "Hi there!", "mode": "light"},
        ]

        response = await test_client.get(f"/sessions/{session_id}/messages")

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) == 2

    @pytest.mark.asyncio
    @patch("agent.memory.delete_session")
    async def test_delete_session(self, mock_delete, test_client):
        session_id = make_session_id()
        mock_delete.return_value = None

        response = await test_client.delete(f"/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True


class TestVoiceEndpoints:
    """Tests for /voice/ endpoints."""

    @pytest.mark.asyncio
    @patch("api.routes.voice.httpx.AsyncClient")
    async def test_tts_returns_audio(self, mock_client_cls, test_client):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            content=b"\xff\xfb\x90\x00" * 100,  # fake mp3 bytes
            headers={"content-type": "audio/mpeg"},
        ))
        mock_client_cls.return_value = mock_client

        response = await test_client.post("/voice/tts", json={
            "text": "Hello, this is a test of the TTS system.",
        })

        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("api.routes.voice.httpx.AsyncClient")
    async def test_stt_accepts_audio_file(self, mock_client_cls, test_client):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {"text": "What is the traffic like today"},
        ))
        mock_client_cls.return_value = mock_client

        # Create fake audio file
        audio_content = b"\xff\xfb\x90\x00" * 50
        response = await test_client.post(
            "/voice/stt",
            files={"file": ("audio.mp3", audio_content, "audio/mpeg")},
        )

        assert response.status_code == 200
        data = response.json()
        assert "text" in data


class TestMetricsEndpoint:
    """Tests for /metrics/ endpoints."""

    @pytest.mark.asyncio
    @patch("api.routes.metrics.duckdb")
    async def test_metrics_returns_summary(self, mock_duckdb, test_client):
        mock_conn = MagicMock()
        mock_conn.execute.return_value = MagicMock(
            fetchone=lambda: (100, 250.5, 1500.0, 50.0, 3, 5),
            fetchall=lambda: [("/chat", 80, 200.3), ("/health", 20, 5.1)],
        )
        mock_duckdb.connect.return_value = mock_conn

        response = await test_client.get("/metrics/")

        assert response.status_code == 200
