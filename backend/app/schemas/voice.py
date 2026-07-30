"""Owner: voice input. Pydantic DTOs for the speech-to-text endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class VoiceTranscribeResponse(BaseModel):
    text: str
    language: str  # "en" | "si" | "ta" — the language actually spoken, never translated
    confidence: float
