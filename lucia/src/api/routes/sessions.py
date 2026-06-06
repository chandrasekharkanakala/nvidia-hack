"""Session management routes."""

import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def list_sessions():
    """List all chat sessions."""
    try:
        from agent import memory

        sessions = await memory.list_sessions()
        return {"sessions": sessions}
    except Exception as e:
        logger.exception("Failed to list sessions")
        return {"sessions": [], "error": str(e)}


@router.get("/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Get message history for a session."""
    try:
        from agent import memory

        messages = await memory.load_history(session_id)
        return {"session_id": session_id, "messages": messages}
    except Exception as e:
        logger.exception(f"Failed to load messages for session {session_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its history."""
    try:
        from agent import memory

        await memory.delete_session(session_id)
        return {"deleted": True, "session_id": session_id}
    except Exception as e:
        logger.exception(f"Failed to delete session {session_id}")
        raise HTTPException(status_code=500, detail=str(e))
