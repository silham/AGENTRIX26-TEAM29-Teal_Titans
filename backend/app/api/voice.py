"""Owner: voice input. Speech-to-text endpoint backing the goal input box.

Routes (protected by get_current_user):
  POST /voice/transcribe   audio blob -> verbatim transcript + detected language
  GET  /voice/_ping        health probe

This is the fallback path for browsers without Web Speech API support
(Safari/iOS, Firefox): the frontend records with MediaRecorder and posts the
blob here. Browsers that DO support native SpeechRecognition (Chrome, Edge)
transcribe client-side and never call this endpoint — see
frontend/components/VoiceInputButton.tsx.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.auth.jwt import CurrentUser, get_current_user
from app.documents.validation import read_capped
from app.llm.gemini_audio import GeminiAudioError, GeminiQuotaExceeded, transcribe_audio
from app.schemas.voice import VoiceTranscribeResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

# One goal statement is a few seconds to a couple of minutes of speech even at
# poor bitrates; generous enough for that without accepting an accidental
# multi-hour recording.
MAX_AUDIO_BYTES = 15 * 1024 * 1024

_MIME_ALLOWLIST = frozenset({
    "audio/webm", "audio/ogg", "audio/mp4", "audio/aac", "audio/mpeg", "audio/wav", "audio/x-wav",
})


@router.get("/_ping")
def ping(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"ok": True}


@router.post("/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form("en", description="Citizen's current language picker — a hint only."),
    user: CurrentUser = Depends(get_current_user),
) -> VoiceTranscribeResponse:
    mime_type = (file.content_type or "audio/webm").split(";")[0].strip().lower()
    if mime_type not in _MIME_ALLOWLIST:
        raise HTTPException(status_code=415, detail=f"Unsupported audio type '{mime_type}'.")

    audio_bytes = await read_capped(file, max_bytes=MAX_AUDIO_BYTES)

    try:
        result = await transcribe_audio(audio_bytes, mime_type=mime_type, language_hint=language)
    except GeminiQuotaExceeded as exc:
        raise HTTPException(
            status_code=503, detail="Voice transcription is temporarily unavailable."
        ) from exc
    except GeminiAudioError as exc:
        logger.error("Voice transcription failed: %s", exc)
        raise HTTPException(
            status_code=502, detail="Could not transcribe audio. Please try typing instead."
        ) from exc

    if not result.text:
        raise HTTPException(status_code=422, detail="No speech detected. Please try again.")

    return VoiceTranscribeResponse(
        text=result.text, language=result.language, confidence=result.confidence
    )
