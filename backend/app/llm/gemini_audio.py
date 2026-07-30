"""Owner: voice input. Gemini 2.5 Flash speech-to-text wrapper.

Responsibilities:
- Send recorded citizen speech to Gemini
- Return a VERBATIM transcript in whatever language/script was spoken, plus
  the detected language

This is the fallback path only: browsers with native Web Speech API support
(Chrome, Edge) transcribe client-side and never reach this module. It exists
so Safari/iOS and other browsers without SpeechRecognition still get full
Sinhala/Tamil/English coverage.

The transcript is never translated here — same "citizen's own words" invariant
as typed input (see agents.md #27). It is handed to the caller exactly as
spoken; app.i18n.understand normalises it to English later, at the same point
typed goals are normalised.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.config import settings
from app.i18n.glossary import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

# gemini-1.5-flash was retired by Google; 2.5-flash is the current free-tier
# model and accepts inline audio parts the same way gemini_vision.py sends images.
MODEL = "gemini-2.5-flash"


class GeminiQuotaExceeded(Exception):
    """Raised when Gemini free-tier quota is exhausted."""


class GeminiAudioError(Exception):
    """Raised for unexpected Gemini API errors."""


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str  # "en" | "si" | "ta"
    confidence: float


_PROMPT = """
You transcribe spoken audio from a Sri Lankan citizen describing a government
service need (for example: "I lost my NIC and need a passport").

The citizen's language picker is currently set to "{language_hint}" — a hint
only, since citizens often speak a different language than the picker. Trust
what you actually hear over this hint.

Respond ONLY with valid JSON — no markdown, no explanation:
{{"text": "<verbatim transcript>", "language": "<en|si|ta>", "confidence": <float 0.0-1.0>}}

Rules:
- Transcribe verbatim. Do NOT translate, summarise, correct grammar, or answer
  the citizen's request.
- If the citizen spoke Sinhala, write the transcript in Sinhala script (not
  romanised). If Tamil, write it in Tamil script. If English, write English.
- "language" is the language actually spoken: "si" for Sinhala, "ta" for
  Tamil, "en" for English.
- If the audio is silent, unintelligible, or not speech, return exactly
  {{"text": "", "language": "en", "confidence": 0.0}}.
"""


async def transcribe_audio(
    audio_bytes: bytes,
    mime_type: str = "audio/webm",
    language_hint: str = DEFAULT_LANGUAGE,
) -> TranscriptionResult:
    """
    Send audio_bytes to Gemini 2.5 Flash and return a verbatim transcript.

    `language_hint` is the citizen's current language picker, passed through
    only to help Gemini on short or ambiguous clips — it never overrides what
    was actually said (see `InputAnalysis` in app.i18n.understand for the same
    "hint, not truth" pattern applied to typed input).

    Raises:
        GeminiQuotaExceeded: when free-tier quota is exhausted.
        GeminiAudioError:    for other unexpected API failures, or a malformed response.
    """
    import google.generativeai as genai
    from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable

    if not settings.gemini_api_key:
        raise GeminiAudioError(
            "GEMINI_API_KEY is not set. Add it to your .env file and restart the server."
        )

    if language_hint not in SUPPORTED_LANGUAGES:
        language_hint = DEFAULT_LANGUAGE

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(MODEL)
    prompt = _PROMPT.format(language_hint=language_hint)

    try:
        response = model.generate_content(
            [{"mime_type": mime_type, "data": audio_bytes}, prompt],
            generation_config=genai.GenerationConfig(temperature=0.0, max_output_tokens=512),
        )
    except ResourceExhausted as exc:
        logger.warning("Gemini quota exhausted during transcription: %s", exc)
        raise GeminiQuotaExceeded("Gemini free-tier quota exhausted.") from exc
    except ServiceUnavailable as exc:
        raise GeminiAudioError(f"Gemini service unavailable: {exc}") from exc
    except Exception as exc:
        raise GeminiAudioError(f"Unexpected Gemini error: {exc}") from exc

    raw_text = response.text.strip()
    logger.debug("Gemini transcription raw response: %s", raw_text)
    return _parse_response(raw_text)


def _parse_response(raw_text: str) -> TranscriptionResult:
    cleaned = raw_text
    if cleaned.startswith("```"):
        cleaned = "\n".join(line for line in cleaned.splitlines() if not line.startswith("```"))

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Gemini transcription JSON: %s\nRaw: %s", exc, raw_text)
        raise GeminiAudioError("Could not parse transcription response.") from exc

    language = str(data.get("language") or DEFAULT_LANGUAGE).strip().lower()
    if language not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE

    return TranscriptionResult(
        text=str(data.get("text") or "").strip(),
        language=language,
        confidence=float(data.get("confidence", 0.5)),
    )
