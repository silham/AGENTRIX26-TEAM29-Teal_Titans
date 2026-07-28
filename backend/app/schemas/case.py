"""Case/step DTOs."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CaseCreate(BaseModel):
    goal: str
    language: str = "en"


class StepStatusUpdate(BaseModel):
    """Citizen marks a step done (or undoes it)."""

    status: Literal["completed", "pending"]


class StepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ord: int
    title: str
    description: str | None = None
    status: str
    depends_on: list = []
    source_url: str | None = None
    reason: str | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: str | None = None
    status: str
    issues: list = []


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    goal: str
    status: str
    progress: int
    current_step_id: UUID | None = None
    language: str
    created_at: datetime
    updated_at: datetime


class CitationOut(BaseModel):
    """A source behind the plan.

    ``origin`` is the trust boundary the UI renders: "rules" = verified official
    procedure, "uploaded_document" = a passage from the admin knowledge base.
    ``source_url`` is None for uploaded documents with no public URL.
    """

    title: str
    source_url: str | None = None
    origin: str = "rules"
    snippet: str | None = None
    score: float | None = None


class CaseDetail(CaseOut):
    steps: list[StepOut] = []
    documents: list[DocumentOut] = []
    citations: list[CitationOut] = []
