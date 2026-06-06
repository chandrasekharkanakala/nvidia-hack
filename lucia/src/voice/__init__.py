"""Voice module — ElevenLabs STT and TTS integration."""

import logging

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel


async def transcribe(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Transcribe audio bytes to text using ElevenLabs STT."""
    try:
        api_key = settings.elevenlabs_api_key if hasattr(settings, "elevenlabs_api_key") else ""
        if not api_key:
            return "[STT unavailable — no ElevenLabs API key configured]"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{ELEVENLABS_BASE_URL}/speech-to-text",
                headers={"xi-api-key": api_key},
                files={"file": (filename, audio_bytes)},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("text", "")

    except httpx.HTTPStatusError as e:
        logger.error(f"ElevenLabs STT HTTP error: {e.response.status_code}")
        return f"[STT error: HTTP {e.response.status_code}]"
    except Exception as e:
        logger.exception("ElevenLabs STT failed")
        return f"[STT error: {str(e)}]"


async def synthesize(text: str, voice_id: str | None = None) -> bytes:
    """Synthesize text to speech using ElevenLabs TTS."""
    try:
        api_key = settings.elevenlabs_api_key if hasattr(settings, "elevenlabs_api_key") else ""
        if not api_key:
            return b""

        voice = voice_id or DEFAULT_VOICE_ID

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                },
            )
            response.raise_for_status()
            return response.content

    except httpx.HTTPStatusError as e:
        logger.error(f"ElevenLabs TTS HTTP error: {e.response.status_code}")
        return b""
    except Exception as e:
        logger.exception("ElevenLabs TTS failed")
        return b""
