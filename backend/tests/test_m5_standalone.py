"""
tests/test_m5_standalone.py  —  M5 standalone tests (no DB / no other members needed)

These tests cover the three files that have zero external dependencies:
  - app/schemas/document.py
  - app/llm/gemini_vision.py   (mocked so no real API key is needed)
  - app/documents/ocr.py       (mocked so no Tesseract binary is needed)
  - app/documents/storage.py   (mocked so no Supabase account is needed)

Run:
    cd backend
    pytest tests/test_m5_standalone.py -v
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Schemas tests
# ---------------------------------------------------------------------------


class TestDocumentSchemas:
    def test_document_status_enum_values(self):
        from app.schemas.document import DocumentStatus

        assert DocumentStatus.ACCEPTED == "accepted"
        assert DocumentStatus.REJECTED == "rejected"
        assert DocumentStatus.MISSING == "missing"
        assert DocumentStatus.INCOMPLETE == "incomplete"
        assert DocumentStatus.NEEDS_VERIFICATION == "needs_verification"

    def test_document_type_enum_values(self):
        from app.schemas.document import DocumentType

        assert DocumentType.NIC == "NIC"
        assert DocumentType.PASSPORT == "passport"
        assert DocumentType.UNKNOWN == "unknown"

    def test_document_upload_response_valid(self):
        from datetime import datetime

        from app.schemas.document import DocumentStatus, DocumentType, DocumentUploadResponse

        resp = DocumentUploadResponse(
            id="doc-001",
            case_id="case-001",
            name="NIC",
            detected_type=DocumentType.NIC,
            status=DocumentStatus.ACCEPTED,
            issues=[],
            confidence=0.95,
            signed_url="https://example.com/signed",
            uploaded_at=datetime.utcnow(),
        )
        assert resp.status == DocumentStatus.ACCEPTED
        assert resp.confidence == 0.95

    def test_vision_analysis_result_defaults(self):
        from app.schemas.document import DocumentType, VisionAnalysisResult

        result = VisionAnalysisResult()
        assert result.detected_type == DocumentType.UNKNOWN
        assert result.issues == []
        assert result.confidence == 0.0

    def test_form_explain_request(self):
        from app.schemas.document import FormExplainRequest

        req = FormExplainRequest(
            case_id="case-001",
            form_name="Passport Application Form",
            fields=["Permanent Address", "Divisional Secretariat"],
            language="en",
        )
        assert len(req.fields) == 2

    def test_form_validate_response_invalid(self):
        from app.schemas.document import FormFieldIssue, FormValidateResponse

        resp = FormValidateResponse(
            form_name="NIC Application Form",
            is_valid=False,
            issues=[
                FormFieldIssue(
                    field="Date of Birth",
                    issue="Invalid date format",
                    suggestion="Use DD/MM/YYYY format",
                )
            ],
            summary="1 issue found",
        )
        assert not resp.is_valid
        assert resp.issues[0].field == "Date of Birth"


# ---------------------------------------------------------------------------
# Gemini vision tests (fully mocked)
# ---------------------------------------------------------------------------


class TestGeminiVision:
    """Tests for gemini_vision.py with Gemini API mocked out."""

    def _make_mock_response(self, payload: dict) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.text = json.dumps(payload)
        return mock_resp

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("app.llm.gemini_vision.genai.GenerativeModel")
    @pytest.mark.asyncio
    async def test_analyze_document_accepted(self, mock_model_cls):
        from app.llm.gemini_vision import analyze_document
        from app.schemas.document import DocumentType

        payload = {
            "document_type": "NIC",
            "visible_fields": {"Name": "Kamal Perera", "NIC Number": "199012345678"},
            "issues": [],
            "confidence": 0.96,
            "extracted_text": "National Identity Card Kamal Perera",
        }
        mock_model = MagicMock()
        mock_model.generate_content.return_value = self._make_mock_response(payload)
        mock_model_cls.return_value = mock_model

        result = await analyze_document(b"fake-image-bytes", expected_name="NIC")

        assert result.detected_type == DocumentType.NIC
        assert result.issues == []
        assert result.confidence == 0.96

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("app.llm.gemini_vision.genai.GenerativeModel")
    @pytest.mark.asyncio
    async def test_analyze_document_rejected_blurry(self, mock_model_cls):
        from app.llm.gemini_vision import analyze_document

        payload = {
            "document_type": "Passport",
            "visible_fields": {},
            "issues": ["Image is blurry or unreadable"],
            "confidence": 0.30,
            "extracted_text": "",
        }
        mock_model = MagicMock()
        mock_model.generate_content.return_value = self._make_mock_response(payload)
        mock_model_cls.return_value = mock_model

        result = await analyze_document(b"blurry-bytes", expected_name="Passport")

        assert len(result.issues) == 1
        assert "blurry" in result.issues[0].lower()
        assert result.confidence == 0.30

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("app.llm.gemini_vision.genai.GenerativeModel")
    @pytest.mark.asyncio
    async def test_analyze_document_handles_malformed_json(self, mock_model_cls):
        """If Gemini returns non-JSON, we should get a safe fallback result."""
        from app.llm.gemini_vision import analyze_document
        from app.schemas.document import DocumentType

        mock_resp = MagicMock()
        mock_resp.text = "Sorry, I cannot analyse this image."
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_resp
        mock_model_cls.return_value = mock_model

        result = await analyze_document(b"bytes", expected_name="NIC")

        assert result.detected_type == DocumentType.UNKNOWN
        assert len(result.issues) > 0

    @patch.dict("os.environ", {}, clear=True)
    @pytest.mark.asyncio
    async def test_analyze_document_raises_when_no_api_key(self):
        from app.llm.gemini_vision import GeminiVisionError, analyze_document

        with pytest.raises(GeminiVisionError, match="GEMINI_API_KEY"):
            await analyze_document(b"bytes", expected_name="NIC")

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("app.llm.gemini_vision.genai.GenerativeModel")
    @pytest.mark.asyncio
    async def test_analyze_document_quota_exceeded(self, mock_model_cls):
        from google.api_core.exceptions import ResourceExhausted

        from app.llm.gemini_vision import GeminiQuotaExceeded, analyze_document

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = ResourceExhausted("quota exceeded")
        mock_model_cls.return_value = mock_model

        with pytest.raises(GeminiQuotaExceeded):
            await analyze_document(b"bytes", expected_name="NIC")


# ---------------------------------------------------------------------------
# OCR tests (Tesseract mocked)
# ---------------------------------------------------------------------------


class TestOCR:
    """Tests for ocr.py with pytesseract mocked."""

    @patch("app.documents.ocr.pytesseract.image_to_string")
    @patch("app.documents.ocr.Image.open")
    def test_extract_text_returns_string(self, mock_open, mock_ocr):
        from app.documents.ocr import extract_text

        mock_image = MagicMock()
        mock_image.convert.return_value.size = (800, 600)
        mock_open.return_value = mock_image
        mock_ocr.return_value = "National Identity Card Kamal Perera 199012345678"

        result = extract_text(b"fake-image-bytes")

        assert "National Identity Card" in result

    @patch("app.documents.ocr.pytesseract.image_to_string")
    @patch("app.documents.ocr.Image.open")
    def test_classify_nic(self, mock_open, mock_ocr):
        from app.documents.ocr import classify_from_ocr_text
        from app.schemas.document import DocumentType

        mock_open.return_value = MagicMock()
        mock_open.return_value.convert.return_value.size = (800, 600)
        mock_ocr.return_value = "National Identity Card Sri Lanka NIC Number 199012345678"

        result = classify_from_ocr_text(b"fake-bytes", expected_name="NIC")

        assert result.detected_type == DocumentType.NIC
        assert result.confidence > 0

    @patch("app.documents.ocr.pytesseract.image_to_string")
    @patch("app.documents.ocr.Image.open")
    def test_classify_passport(self, mock_open, mock_ocr):
        from app.documents.ocr import classify_from_ocr_text
        from app.schemas.document import DocumentType

        mock_open.return_value = MagicMock()
        mock_ocr.return_value = "Republic of Sri Lanka Passport Department of Immigration Place of Birth"

        result = classify_from_ocr_text(b"fake-bytes", expected_name="Passport")

        assert result.detected_type == DocumentType.PASSPORT

    @patch("app.documents.ocr.pytesseract.image_to_string")
    @patch("app.documents.ocr.Image.open")
    def test_blurry_image_flagged(self, mock_open, mock_ocr):
        from app.documents.ocr import classify_from_ocr_text

        mock_open.return_value = MagicMock()
        mock_ocr.return_value = ""  # Nothing extracted = blurry

        result = classify_from_ocr_text(b"blurry", expected_name="NIC")

        assert any("blurry" in issue.lower() or "quality" in issue.lower() for issue in result.issues)

    @patch("app.documents.ocr.Image.open")
    def test_corrupt_image_returns_safe_fallback(self, mock_open):
        from app.documents.ocr import classify_from_ocr_text
        from app.schemas.document import DocumentType

        mock_open.side_effect = Exception("cannot identify image file")

        result = classify_from_ocr_text(b"corrupted-bytes", expected_name="NIC")

        assert result.detected_type == DocumentType.UNKNOWN
        assert len(result.issues) > 0


# ---------------------------------------------------------------------------
# Storage tests (Supabase mocked)
# ---------------------------------------------------------------------------


class TestStorage:
    """Tests for storage.py with Supabase SDK mocked."""

    @patch.dict(
        "os.environ",
        {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_KEY": "test-key"},
    )
    def test_build_storage_path_structure(self):
        from app.documents.storage import build_storage_path

        path = build_storage_path(
            user_id="user-abc",
            case_id="case-xyz",
            original_filename="my NIC photo.jpg",
        )

        assert path.startswith("user-abc/case-xyz/")
        # Spaces should be replaced with underscores
        assert " " not in path

    @patch.dict(
        "os.environ",
        {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_KEY": "test-key"},
    )
    def test_build_storage_path_unique(self):
        from app.documents.storage import build_storage_path

        path1 = build_storage_path("u1", "c1", "nic.jpg")
        path2 = build_storage_path("u1", "c1", "nic.jpg")

        assert path1 != path2  # UUID prefix ensures uniqueness

    @patch("app.documents.storage._get_client")
    @patch.dict(
        "os.environ",
        {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_KEY": "test-key"},
    )
    @pytest.mark.asyncio
    async def test_upload_file_returns_path(self, mock_get_client):
        from app.documents.storage import upload_file

        mock_client = MagicMock()
        mock_client.storage.from_().upload.return_value = MagicMock()
        mock_get_client.return_value = mock_client

        path = await upload_file(b"image-bytes", "nic.jpg", "user-1", "case-1")

        assert "user-1" in path
        assert "case-1" in path
        mock_client.storage.from_().upload.assert_called_once()

    @patch("app.documents.storage._get_client")
    @patch.dict(
        "os.environ",
        {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_KEY": "test-key"},
    )
    @pytest.mark.asyncio
    async def test_get_signed_url(self, mock_get_client):
        from app.documents.storage import get_signed_url

        mock_client = MagicMock()
        mock_client.storage.from_().create_signed_url.return_value = {
            "signedURL": "https://supabase.co/signed?token=abc"
        }
        mock_get_client.return_value = mock_client

        url = await get_signed_url("user-1/case-1/abc_nic.jpg")

        assert url.startswith("https://")
        assert "signed" in url

    @patch("app.documents.storage._get_client")
    @patch.dict(
        "os.environ",
        {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_KEY": "test-key"},
    )
    @pytest.mark.asyncio
    async def test_delete_file_calls_remove(self, mock_get_client):
        from app.documents.storage import delete_file

        mock_client = MagicMock()
        mock_client.storage.from_().remove.return_value = MagicMock()
        mock_get_client.return_value = mock_client

        await delete_file("user-1/case-1/abc_nic.jpg")

        mock_client.storage.from_().remove.assert_called_once_with(
            ["user-1/case-1/abc_nic.jpg"]
        )

    @patch.dict("os.environ", {}, clear=True)
    @pytest.mark.asyncio
    async def test_upload_raises_when_no_config(self):
        import app.documents.storage as storage_module

        storage_module._supabase_client = None  # reset singleton

        from app.documents.storage import StorageConfigError, upload_file

        with pytest.raises(StorageConfigError):
            await upload_file(b"bytes", "nic.jpg", "user-1", "case-1")
