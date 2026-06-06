"""Voice routes — STT and TTS endpoints."""

import logging

import httpx
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"


class TTSRequest(BaseModel):
    text: str
    voice_id: str | None = None


@router.post("/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    """Transcribe audio file to text using ElevenLabs STT."""
    try:
        audio_bytes = await audio.read()
        api_key = settings.elevenlabs_api_key
        if not api_key:
            return {"text": "[STT unavailable — no API key]"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{ELEVENLABS_BASE_URL}/speech-to-text",
                headers={"xi-api-key": api_key},
                files={"file": (audio.filename or "audio.webm", audio_bytes)},
            )
            response.raise_for_status()
            data = response.json()
            return {"text": data.get("text", "")}
    except Exception as e:
        logger.exception("STT endpoint failed")
        return {"text": "", "error": str(e)}


@router.post("/tts")
async def text_to_speech(body: TTSRequest):
    """Convert text to speech using ElevenLabs TTS."""
    try:
        api_key = settings.elevenlabs_api_key
        if not api_key:
            return Response(content=b"", media_type="audio/mpeg", status_code=500)

        voice_id = body.voice_id or settings.elevenlabs_voice_id

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}",
                headers={"xi-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "text": body.text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                },
            )
            response.raise_for_status()
            return Response(content=response.content, media_type="audio/mpeg")
    except Exception as e:
        logger.exception("TTS endpoint failed")
        return Response(content=b"", media_type="audio/mpeg", status_code=500)
