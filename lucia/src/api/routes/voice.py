"""Voice routes — STT and TTS endpoints."""

import logging

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from src.voice import transcribe, synthesize

logger = logging.getLogger(__name__)
router = APIRouter()


class TTSRequest(BaseModel):
    text: str
    voice_id: str | None = None


@router.post("/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    """Transcribe audio file to text using ElevenLabs STT."""
    try:
        audio_bytes = await audio.read()
        text = await transcribe(audio_bytes, filename=audio.filename or "audio.webm")
        return {"text": text}
    except Exception as e:
        logger.exception("STT endpoint failed")
        return {"text": "", "error": str(e)}


@router.post("/tts")
async def text_to_speech(body: TTSRequest):
    """Convert text to speech using ElevenLabs TTS."""
    try:
        audio_bytes = await synthesize(body.text, voice_id=body.voice_id)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        logger.exception("TTS endpoint failed")
        return Response(content=b"", media_type="audio/mpeg", status_code=500)
