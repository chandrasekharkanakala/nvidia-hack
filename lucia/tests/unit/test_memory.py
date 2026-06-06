"""Unit tests for Memory (conversation CRUD operations)."""

import pytest
from unittest.mock import patch, MagicMock

from tests.factories import make_session_id


@pytest.fixture
def memory_db(test_db):
    """DuckDB with chat_messages table initialized."""
    test_db.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY,
            session_id VARCHAR NOT NULL,
            role VARCHAR NOT NULL,
            content TEXT NOT NULL,
            mode VARCHAR DEFAULT 'light',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    test_db.execute("CREATE SEQUENCE IF NOT EXISTS chat_messages_id_seq START 1")
    return test_db


class TestMemorySaveMessage:
    """Tests for memory.save_message()."""

    @pytest.mark.asyncio
    @patch("agent.memory.duckdb")
    async def test_save_user_message(self, mock_duckdb, memory_db):
        mock_duckdb.connect.return_value = memory_db
        from agent.memory import save_message

        session_id = make_session_id()
        await save_message(session_id, "user", "Hello world", "light")

        result = memory_db.execute(
            "SELECT role, content, mode FROM chat_messages WHERE session_id = ?",
            [session_id]
        ).fetchall()

        assert len(result) == 1
        assert result[0][0] == "user"
        assert result[0][1] == "Hello world"
        assert result[0][2] == "light"

    @pytest.mark.asyncio
    @patch("agent.memory.duckdb")
    async def test_save_assistant_message(self, mock_duckdb, memory_db):
        mock_duckdb.connect.return_value = memory_db
        from agent.memory import save_message

        session_id = make_session_id()
        await save_message(session_id, "assistant", "Here is the answer", "deep")

        result = memory_db.execute(
            "SELECT role, mode FROM chat_messages WHERE session_id = ?",
            [session_id]
        ).fetchall()

        assert result[0][0] == "assistant"
        assert result[0][1] == "deep"

    @pytest.mark.asyncio
    @patch("agent.memory.duckdb")
    async def test_save_multiple_messages(self, mock_duckdb, memory_db):
        mock_duckdb.connect.return_value = memory_db
        from agent.memory import save_message

        session_id = make_session_id()
        await save_message(session_id, "user", "Question 1", "light")
        await save_message(session_id, "assistant", "Answer 1", "light")
        await save_message(session_id, "user", "Question 2", "light")

        count = memory_db.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE session_id = ?",
            [session_id]
        ).fetchone()[0]

        assert count == 3


class TestMemoryLoadHistory:
    """Tests for memory.load_history()."""

    @pytest.mark.asyncio
    @patch("agent.memory.duckdb")
    async def test_load_recent_messages(self, mock_duckdb, memory_db):
        mock_duckdb.connect.return_value = memory_db
        from agent.memory import save_message, load_history

        session_id = make_session_id()
        await save_message(session_id, "user", "First message", "light")
        await save_message(session_id, "assistant", "First reply", "light")
        await save_message(session_id, "user", "Second message", "light")

        history = await load_history(session_id)

        assert isinstance(history, list)
        assert len(history) == 3

    @pytest.mark.asyncio
    @patch("agent.memory.duckdb")
    async def test_load_with_limit(self, mock_duckdb, memory_db):
        mock_duckdb.connect.return_value = memory_db
        from agent.memory import save_message, load_history

        session_id = make_session_id()
        for i in range(15):
            await save_message(session_id, "user", f"Message {i}", "light")

        history = await load_history(session_id, limit=5)

        assert len(history) <= 5

    @pytest.mark.asyncio
    @patch("agent.memory.duckdb")
    async def test_load_empty_session(self, mock_duckdb, memory_db):
        mock_duckdb.connect.return_value = memory_db
        from agent.memory import load_history

        history = await load_history(make_session_id())

        assert history == []

    @pytest.mark.asyncio
    @patch("agent.memory.duckdb")
    async def test_messages_have_required_fields(self, mock_duckdb, memory_db):
        mock_duckdb.connect.return_value = memory_db
        from agent.memory import save_message, load_history

        session_id = make_session_id()
        await save_message(session_id, "user", "Test", "light")

        history = await load_history(session_id)

        msg = history[0]
        assert "role" in msg
        assert "content" in msg
        assert "mode" in msg


class TestMemoryListSessions:
    """Tests for memory.list_sessions()."""

    @pytest.mark.asyncio
    @patch("agent.memory.duckdb")
    async def test_list_returns_sessions(self, mock_duckdb, memory_db):
        mock_duckdb.connect.return_value = memory_db
        from agent.memory import save_message, list_sessions

        s1 = make_session_id()
        s2 = make_session_id()
        await save_message(s1, "user", "Hello from session 1", "light")
        await save_message(s2, "user", "Hello from session 2", "deep")

        sessions = await list_sessions()

        assert isinstance(sessions, list)
        assert len(sessions) >= 2

    @pytest.mark.asyncio
    @patch("agent.memory.duckdb")
    async def test_session_has_metadata(self, mock_duckdb, memory_db):
        mock_duckdb.connect.return_value = memory_db
        from agent.memory import save_message, list_sessions

        session_id = make_session_id()
        await save_message(session_id, "user", "This is my first message in the session", "light")
        await save_message(session_id, "assistant", "Reply", "light")

        sessions = await list_sessions()
        session = next((s for s in sessions if s.get("id") == session_id), None)

        if session:
            assert "title" in session or "id" in session
            assert "message_count" in session or "last_activity" in session


class TestMemoryDeleteSession:
    """Tests for memory.delete_session()."""

    @pytest.mark.asyncio
    @patch("agent.memory.duckdb")
    async def test_delete_removes_messages(self, mock_duckdb, memory_db):
        mock_duckdb.connect.return_value = memory_db
        from agent.memory import save_message, delete_session, load_history

        session_id = make_session_id()
        await save_message(session_id, "user", "Message to delete", "light")
        await save_message(session_id, "assistant", "Reply to delete", "light")

        await delete_session(session_id)

        history = await load_history(session_id)
        assert history == []

    @pytest.mark.asyncio
    @patch("agent.memory.duckdb")
    async def test_delete_nonexistent_session_no_error(self, mock_duckdb, memory_db):
        mock_duckdb.connect.return_value = memory_db
        from agent.memory import delete_session

        # Should not raise
        await delete_session(make_session_id())

    @pytest.mark.asyncio
    @patch("agent.memory.duckdb")
    async def test_delete_does_not_affect_other_sessions(self, mock_duckdb, memory_db):
        mock_duckdb.connect.return_value = memory_db
        from agent.memory import save_message, delete_session, load_history

        s1 = make_session_id()
        s2 = make_session_id()
        await save_message(s1, "user", "Session 1", "light")
        await save_message(s2, "user", "Session 2", "light")

        await delete_session(s1)

        history_s2 = await load_history(s2)
        assert len(history_s2) == 1
