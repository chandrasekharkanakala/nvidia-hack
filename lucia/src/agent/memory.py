"""LUCIA Agent — Conversation memory backed by DuckDB."""

import duckdb
from datetime import datetime, timezone

from config.settings import settings

_CON: duckdb.DuckDBPyConnection | None = None


def _get_con() -> duckdb.DuckDBPyConnection:
    global _CON
    if _CON is None:
        _CON = duckdb.connect(settings.duckdb_path)
        _CON.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY DEFAULT nextval('chat_messages_seq'),
                session_id VARCHAR NOT NULL,
                role VARCHAR NOT NULL,
                content TEXT NOT NULL,
                mode VARCHAR DEFAULT 'light',
                created_at TIMESTAMP DEFAULT current_timestamp
            )
        """)
        _CON.execute("CREATE SEQUENCE IF NOT EXISTS chat_messages_seq START 1")
    return _CON


def _ensure_table() -> None:
    con = _get_con()
    try:
        con.execute("SELECT 1 FROM chat_messages LIMIT 0")
    except duckdb.CatalogException:
        con.execute("""
            CREATE SEQUENCE IF NOT EXISTS chat_messages_seq START 1;
            CREATE TABLE chat_messages (
                id INTEGER PRIMARY KEY DEFAULT nextval('chat_messages_seq'),
                session_id VARCHAR NOT NULL,
                role VARCHAR NOT NULL,
                content TEXT NOT NULL,
                mode VARCHAR DEFAULT 'light',
                created_at TIMESTAMP DEFAULT current_timestamp
            )
        """)


async def load_history(session_id: str, limit: int = 10) -> list[dict]:
    """Load recent conversation history for a session."""
    try:
        con = _get_con()
        rows = con.execute(
            """SELECT role, content, mode, created_at
               FROM chat_messages
               WHERE session_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            [session_id, limit],
        ).fetchall()
        return [
            {"role": r[0], "content": r[1], "mode": r[2], "created_at": str(r[3])}
            for r in reversed(rows)
        ]
    except Exception:
        return []


async def save_message(session_id: str, role: str, content: str, mode: str) -> None:
    """Persist a message to the conversation store."""
    try:
        con = _get_con()
        con.execute(
            """INSERT INTO chat_messages (session_id, role, content, mode, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            [session_id, role, content, mode, datetime.now(timezone.utc)],
        )
    except Exception:
        pass


async def list_sessions() -> list[dict]:
    """List all sessions with metadata."""
    try:
        con = _get_con()
        rows = con.execute("""
            SELECT
                session_id,
                MIN(content) FILTER (WHERE role = 'user') AS first_msg,
                MAX(created_at) AS last_activity,
                COUNT(*) AS message_count
            FROM chat_messages
            GROUP BY session_id
            ORDER BY last_activity DESC
        """).fetchall()
        return [
            {
                "id": r[0],
                "title": (r[1][:60] + "...") if r[1] and len(r[1]) > 60 else (r[1] or ""),
                "last_activity": str(r[2]),
                "message_count": r[3],
            }
            for r in rows
        ]
    except Exception:
        return []


async def delete_session(session_id: str) -> None:
    """Delete all messages for a session."""
    try:
        con = _get_con()
        con.execute("DELETE FROM chat_messages WHERE session_id = ?", [session_id])
    except Exception:
        pass
