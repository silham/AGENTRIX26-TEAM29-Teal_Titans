"""Owner: voice input.

Covers:
  - app/llm/gemini_audio.py   (mocked so no real API key is needed)
  - app/api/voice.py          (endpoint-level: validation, error mapping, auth)
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.auth.jwt import CurrentUser, get_current_user
from app.main import app

USER = CurrentUser(id="user-1", email="citizen@example.lk", role="user")


# ---------------------------------------------------------------------------
# Gemini audio transcription (fully mocked)
# ---------------------------------------------------------------------------


class TestGeminiAudio:
    def _make_mock_response(self, payload: dict):
        from unittest.mock import MagicMock

        mock_resp = MagicMock()
        mock_resp.text = json.dumps(payload)
        return mock_resp

    def _install_mock_model(self, monkeypatch, mock_model) -> None:
        import google.generativeai as genai

        from app.config import settings

        monkeypatch.setattr(settings, "gemini_api_key", "test-key")
        monkeypatch.setattr(genai, "configure", lambda **kw: None)
        monkeypatch.setattr(genai, "GenerativeModel", lambda *a, **kw: mock_model)

    @pytest.mark.asyncio
    async def test_transcribe_sinhala_speech(self, monkeypatch):
        from unittest.mock import MagicMock

        from app.llm.gemini_audio import transcribe_audio

        payload = {"text": "මගේ ජාතික හැඳුනුම්පත නැති වුණා", "language": "si", "confidence": 0.92}
        mock_model = MagicMock()
        mock_model.generate_content.return_value = self._make_mock_response(payload)
        self._install_mock_model(monkeypatch, mock_model)

        result = await transcribe_audio(b"fake-audio-bytes", mime_type="audio/webm")

        assert result.language == "si"
        assert result.text == payload["text"]
        assert result.confidence == 0.92

    @pytest.mark.asyncio
    async def test_transcribe_never_translates_the_transcript(self, monkeypatch):
        """The transcript must survive verbatim — same invariant as typed input (agents.md #27)."""
        from unittest.mock import MagicMock

        from app.llm.gemini_audio import transcribe_audio

        tamil_text = "என் அடையாள அட்டை தொலைந்துவிட்டது"
        payload = {"text": tamil_text, "language": "ta", "confidence": 0.88}
        mock_model = MagicMock()
        mock_model.generate_content.return_value = self._make_mock_response(payload)
        self._install_mock_model(monkeypatch, mock_model)

        result = await transcribe_audio(b"bytes", mime_type="audio/webm", language_hint="en")

        assert result.text == tamil_text
        assert result.language == "ta"

    @pytest.mark.asyncio
    async def test_transcribe_handles_silence(self, monkeypatch):
        from unittest.mock import MagicMock

        from app.llm.gemini_audio import transcribe_audio

        payload = {"text": "", "language": "en", "confidence": 0.0}
        mock_model = MagicMock()
        mock_model.generate_content.return_value = self._make_mock_response(payload)
        self._install_mock_model(monkeypatch, mock_model)

        result = await transcribe_audio(b"silence")

        assert result.text == ""

    @pytest.mark.asyncio
    async def test_transcribe_handles_malformed_json(self, monkeypatch):
        from unittest.mock import MagicMock

        from app.llm.gemini_audio import GeminiAudioError, transcribe_audio

        mock_resp = MagicMock()
        mock_resp.text = "I cannot process this audio."
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_resp
        self._install_mock_model(monkeypatch, mock_model)

        with pytest.raises(GeminiAudioError):
            await transcribe_audio(b"bytes")

    @pytest.mark.asyncio
    async def test_transcribe_raises_when_no_api_key(self, monkeypatch):
        from app.config import settings
        from app.llm.gemini_audio import GeminiAudioError, transcribe_audio

        monkeypatch.setattr(settings, "gemini_api_key", "")

        with pytest.raises(GeminiAudioError, match="GEMINI_API_KEY"):
            await transcribe_audio(b"bytes")

    @pytest.mark.asyncio
    async def test_transcribe_quota_exceeded(self, monkeypatch):
        from unittest.mock import MagicMock

        from google.api_core.exceptions import ResourceExhausted

        from app.llm.gemini_audio import GeminiQuotaExceeded, transcribe_audio

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = ResourceExhausted("quota exceeded")
        self._install_mock_model(monkeypatch, mock_model)

        with pytest.raises(GeminiQuotaExceeded):
            await transcribe_audio(b"bytes")

    @pytest.mark.asyncio
    async def test_invalid_language_hint_falls_back_to_default(self, monkeypatch):
        """An unsupported hint (e.g. stale client state) must not reach the prompt raw."""
        from unittest.mock import MagicMock

        from app.llm.gemini_audio import transcribe_audio

        payload = {"text": "hello", "language": "en", "confidence": 0.5}
        mock_model = MagicMock()
        mock_model.generate_content.return_value = self._make_mock_response(payload)
        self._install_mock_model(monkeypatch, mock_model)

        result = await transcribe_audio(b"bytes", language_hint="fr")

        assert result.language == "en"


# ---------------------------------------------------------------------------
# /voice/transcribe endpoint
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: USER
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def _upload(client, body=b"x" * 500, content_type="audio/webm", **data):
    return client.post(
        "/voice/transcribe",
        files={"file": ("clip.webm", body, content_type)},
        data=data,
    )


def test_transcribe_endpoint_returns_text_and_language(client, monkeypatch):
    from app.llm.gemini_audio import TranscriptionResult

    async def _fake_transcribe(audio_bytes, mime_type="audio/webm", language_hint="en"):
        return TranscriptionResult(text="I lost my NIC", language="en", confidence=0.9)

    monkeypatch.setattr("app.api.voice.transcribe_audio", _fake_transcribe)

    r = _upload(client, language="en")

    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "I lost my NIC"
    assert body["language"] == "en"


def test_transcribe_endpoint_rejects_unsupported_mime_type(client):
    r = _upload(client, content_type="video/mp4")
    assert r.status_code == 415


def test_transcribe_endpoint_rejects_oversized_upload(client, monkeypatch):
    from app.api import voice as voice_api

    monkeypatch.setattr(voice_api, "MAX_AUDIO_BYTES", 100)
    r = _upload(client, body=b"x" * 1000)
    assert r.status_code == 413


def test_transcribe_endpoint_returns_422_on_silence(client, monkeypatch):
    from app.llm.gemini_audio import TranscriptionResult

    async def _fake_transcribe(audio_bytes, mime_type="audio/webm", language_hint="en"):
        return TranscriptionResult(text="", language="en", confidence=0.0)

    monkeypatch.setattr("app.api.voice.transcribe_audio", _fake_transcribe)

    r = _upload(client)
    assert r.status_code == 422


def test_transcribe_endpoint_maps_quota_exceeded_to_503(client, monkeypatch):
    from app.llm.gemini_audio import GeminiQuotaExceeded

    async def _fake_transcribe(audio_bytes, mime_type="audio/webm", language_hint="en"):
        raise GeminiQuotaExceeded("quota exceeded")

    monkeypatch.setattr("app.api.voice.transcribe_audio", _fake_transcribe)

    r = _upload(client)
    assert r.status_code == 503


def test_transcribe_endpoint_requires_auth():
    # No dependency override here — the real get_current_user should reject.
    test_client = TestClient(app)
    r = test_client.post(
        "/voice/transcribe",
        files={"file": ("clip.webm", b"x" * 100, "audio/webm")},
    )
    assert r.status_code in (401, 403)
