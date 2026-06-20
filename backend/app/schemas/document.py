"""Owner: M5. Pydantic DTOs for the document and form-assist domain.

Used by:
  - api/documents.py   (request / response bodies)
  - api/forms.py       (request / response bodies)
  - graph/nodes/document.py  (internal result passing)
  - graph/nodes/form.py      (internal result passing)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DocumentStatus(str, Enum):
    """Lifecycle states of an uploaded document."""

    MISSING = "missing"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INCOMPLETE = "incomplete"
    NEEDS_VERIFICATION = "needs_verification"


class DocumentType(str, Enum):
    """Known Sri Lankan government document types."""

    NIC = "NIC"
    PASSPORT = "passport"
    BIRTH_CERTIFICATE = "birth_certificate"
    POLICE_REPORT = "police_report"
    DRIVING_LICENSE = "driving_license"
    MARRIAGE_CERTIFICATE = "marriage_certificate"
    DEATH_CERTIFICATE = "death_certificate"
    APPLICATION_FORM = "application_form"
    PHOTO = "passport_photo"
    OTHER = "other"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# ORM-mapped output (used by repository layer)
# ---------------------------------------------------------------------------


class DocumentOut(BaseModel):
    """ORM-compatible read model for a Document row."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: str | None = None
    status: str
    issues: list = []


# ---------------------------------------------------------------------------
# Document Upload
# ---------------------------------------------------------------------------


class DocumentUploadRequest(BaseModel):
    """
    Metadata sent alongside the multipart file upload.
    The actual file bytes arrive as a FastAPI UploadFile, not in this model.
    """

    case_id: str = Field(..., description="The citizen case this document belongs to.")
    expected_name: str = Field(
        ...,
        description="Human-readable label, e.g. 'NIC', 'Birth Certificate'.",
        examples=["NIC", "Birth Certificate", "Police Report"],
    )


class DocumentUploadResponse(BaseModel):
    """Returned immediately after upload + verification completes."""

    id: str
    case_id: str
    name: str
    detected_type: DocumentType
    status: DocumentStatus
    issues: list[str] = Field(
        default_factory=list,
        description="Human-readable list of problems found, empty when accepted.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="AI confidence in the verdict (0–1).",
    )
    signed_url: str | None = Field(
        None,
        description="Short-lived pre-signed URL to view the file (if accepted).",
    )
    uploaded_at: datetime


# ---------------------------------------------------------------------------
# Document item (used inside GraphState and dashboard responses)
# ---------------------------------------------------------------------------


class DocumentItem(BaseModel):
    """Lightweight document record stored in GraphState and returned to frontend."""

    id: str
    name: str
    detected_type: DocumentType = DocumentType.UNKNOWN
    status: DocumentStatus = DocumentStatus.MISSING
    issues: list[str] = Field(default_factory=list)
    storage_path: str | None = None
    uploaded_at: datetime | None = None


# ---------------------------------------------------------------------------
# Vision / OCR analysis result (internal — not exposed via API)
# ---------------------------------------------------------------------------


class VisionAnalysisResult(BaseModel):
    """
    Raw output from gemini_vision.py or ocr.py.
    The document node (graph/nodes/document.py) converts this into a verdict.
    """

    detected_type: DocumentType = DocumentType.UNKNOWN
    extracted_text: str = ""
    visible_fields: dict[str, Any] = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    raw_response: str = ""  # full model output for debugging


# ---------------------------------------------------------------------------
# Form Assist
# ---------------------------------------------------------------------------


class FormExplainRequest(BaseModel):
    """Ask the Form Assistant to explain one or more fields."""

    case_id: str
    form_name: str = Field(
        ...,
        description="Name of the government form, e.g. 'Passport Application Form'.",
        examples=["Passport Application Form", "NIC Application Form"],
    )
    fields: list[str] = Field(
        ...,
        description="List of field labels the citizen is confused about.",
        examples=[["Permanent Address", "Divisional Secretariat"]],
    )
    language: str = Field(
        "en",
        description="Response language: 'en', 'si' (Sinhala), or 'ta' (Tamil).",
    )


class FieldExplanation(BaseModel):
    """Explanation for a single form field."""

    field: str
    explanation: str
    example: str | None = None


class FormExplainResponse(BaseModel):
    """Returned by POST /forms/explain."""

    form_name: str
    explanations: list[FieldExplanation]


class FormValidateRequest(BaseModel):
    """Submit a partially or fully filled form for validation."""

    case_id: str
    form_name: str
    filled_data: dict[str, Any] = Field(
        ...,
        description="Key-value pairs of field label → citizen's answer.",
    )
    language: str = "en"


class FormFieldIssue(BaseModel):
    """A single validation problem on a form field."""

    field: str
    issue: str
    suggestion: str | None = None


class FormValidateResponse(BaseModel):
    """Returned by POST /forms/validate."""

    form_name: str
    is_valid: bool
    issues: list[FormFieldIssue] = Field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Generic delete / fetch responses
# ---------------------------------------------------------------------------


class DocumentDeleteResponse(BaseModel):
    id: str
    deleted: bool = True
    message: str = "Document deleted successfully."


class DocumentGetResponse(BaseModel):
    id: str
    case_id: str
    name: str
    detected_type: DocumentType
    status: DocumentStatus
    issues: list[str]
    confidence: float
    signed_url: str | None
    uploaded_at: datetime
