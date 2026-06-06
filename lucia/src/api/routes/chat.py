"""Chat routes — REST and WebSocket endpoints."""

import json
import logging
import uuid

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    content: str
    mode: str = "chat"
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tools_used: list[str] = []
    thinking: str | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    """Process a chat message through the LUCIA agent."""
    try:
        from src.agent import process_message

        session_id = body.session_id or str(uuid.uuid4())

        result = await process_message(
            content=body.content,
            mode=body.mode,
            session_id=session_id,
        )

        return ChatResponse(
            response=result.get("response", ""),
            session_id=session_id,
            tools_used=result.get("tools_used", []),
            thinking=result.get("thinking"),
        )
    except Exception as e:
        logger.exception("Chat endpoint failed")
        return ChatResponse(
            response=f"I encountered an error: {str(e)}",
            session_id=body.session_id or str(uuid.uuid4()),
            tools_used=[],
        )


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat responses."""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            content = message.get("content", "")
            session_id = message.get("session_id", str(uuid.uuid4()))
            mode = message.get("mode", "chat")

            # Send thinking event
            await websocket.send_json({"event": "thinking", "data": {"session_id": session_id}})

            try:
                from src.agent import process_message_stream

                async for event in process_message_stream(
                    content=content, mode=mode, session_id=session_id
                ):
                    await websocket.send_json(event)

            except ImportError:
                # Fallback if streaming not implemented
                from src.agent import process_message

                await websocket.send_json({"event": "tool_start", "data": {"tool": "agent"}})

                result = await process_message(
                    content=content, mode=mode, session_id=session_id
                )

                await websocket.send_json({"event": "tool_end", "data": {"tool": "agent"}})

                # Stream tokens
                response_text = result.get("response", "")
                for i in range(0, len(response_text), 10):
                    chunk = response_text[i : i + 10]
                    await websocket.send_json({"event": "token", "data": {"text": chunk}})

            await websocket.send_json({"event": "done", "data": {"session_id": session_id}})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.exception("WebSocket error")
        try:
            await websocket.send_json({"event": "error", "data": {"message": str(e)}})
        except Exception:
            pass
