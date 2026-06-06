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
    chart: str | None = None  # base64 PNG


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    """Process a chat message through the LUCIA agent."""
    if not body.content.strip():
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={"detail": "content must not be empty"})
    try:
        from agent import process_message, AgentMode

        session_id = body.session_id or str(uuid.uuid4())

        result = await process_message(
            content=body.content,
            mode=AgentMode(body.mode) if body.mode in ("light", "deep") else AgentMode.light,
            session_id=session_id,
        )

        # Extract chart if visualizer was used
        chart_b64 = None
        tool_results = result.get("tool_results", [])
        for tr in tool_results:
            if isinstance(tr, dict) and tr.get("data") and isinstance(tr["data"], dict):
                if tr["data"].get("chart_base64"):
                    chart_b64 = tr["data"]["chart_base64"]
                    break

        return ChatResponse(
            response=result.get("response") or result.get("content", ""),
            session_id=session_id,
            tools_used=result.get("tools_used") or [t.get("tool", t) if isinstance(t, dict) else t for t in result.get("tool_calls", [])],
            thinking=result.get("thinking"),
            chart=chart_b64,
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
            mode_str = message.get("mode", "chat")

            # Send thinking event
            await websocket.send_json({"type": "thinking"})

            result = None
            response_text = ""

            try:
                from agent import process_message_stream, AgentMode as _AgentMode

                _mode = _AgentMode(mode_str) if mode_str in ("light", "deep") else _AgentMode.light
                async for event in process_message_stream(
                    content=content, mode=_mode, session_id=session_id
                ):
                    await websocket.send_json(event)

            except ImportError:
                # Fallback if streaming not implemented
                from agent import process_message, AgentMode as _AgentMode2

                _mode = _AgentMode2(mode_str) if mode_str in ("light", "deep") else _AgentMode2.light
                await websocket.send_json({"type": "tool_start", "tool": "agent", "description": "Processing..."})

                result = await process_message(
                    content=content, mode=_mode, session_id=session_id
                )

                await websocket.send_json({"type": "tool_end", "tool": "agent", "duration_ms": result.get("metrics", {}).get("total_ms", 0), "success": True})

                # Send chart if available
                tool_results = result.get("tool_results", [])
                for tr in tool_results:
                    if isinstance(tr, dict) and tr.get("data") and isinstance(tr["data"], dict):
                        if tr["data"].get("chart_base64"):
                            await websocket.send_json({"type": "chart", "data": tr["data"]["chart_base64"]})
                            break

                # Stream tokens
                response_text = result.get("content") or result.get("response", "")
                for i in range(0, len(response_text), 10):
                    chunk = response_text[i : i + 10]
                    await websocket.send_json({"type": "token", "content": chunk})

            metrics_data = result.get("metrics", {}) if result else {}
            await websocket.send_json({
                "type": "done",
                "metrics": {
                    "latencyMs": metrics_data.get("total_ms", 0),
                    "timeToFirstTokenMs": metrics_data.get("time_to_first_token_ms", 0),
                    "tokensPrompt": metrics_data.get("tokens_prompt", 0),
                    "tokensCompletion": metrics_data.get("tokens_completion", 0) or len(response_text) // 4,
                    "toolsUsed": metrics_data.get("tools_used", []),
                }
            })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.exception("WebSocket error")
        try:
            await websocket.send_json({"event": "error", "data": {"message": str(e)}})
        except Exception:
            pass
