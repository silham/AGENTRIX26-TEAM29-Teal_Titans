"""Case/step DTOs."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CaseCreate(BaseModel):
    # Bounded because this string reaches two separate LLM prompts (input
    # normalisation, then the planner) and was previously unbounded.
    goal: str = Field(min_length=3, max_length=2000)
    # The picker value. Only a HINT: the backend detects the language actually
    # written and that detection wins, because a citizen may type Sinhala
    # without ever having opened the picker.
    language: str = "en"


class StepStatusUpdate(BaseModel):
    """Citizen marks a step done (or undoes it)."""

    status: Literal["completed", "pending"]


class RequirementStatusUpdate(BaseModel):
    """Citizen self-declares that they hold a requirement, or takes it back.

    'confirmed' is deliberately not 'accepted': nothing was uploaded and nothing
    was verified — the citizen simply told us they have it.
    """

    status: Literal["confirmed", "missing"]


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
    # Requirement key this step obtains; confirming that requirement completes it.
    fulfills: str | None = None


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
    # 'citizen' or 'generated'. On the wire because the response localizer
    # branches on it: a citizen's own words are returned verbatim, while a
    # machine-written sub-goal (always composed in English) is translated.
    goal_source: str = "citizen"
    status: str
    progress: int
    current_step_id: UUID | None = None
    # The language DETECTED in the goal — not the render language, which is
    # per-request via the X-Language header. The client reads this after
    # creating a case to auto-switch when the citizen wrote in another language.
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


class ParentRef(BaseModel):
    """The case a sub-goal belongs to, for the "Part of: …" link back."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal: str


class SubGoalOut(BaseModel):
    """A plan spawned from one of this case's requirements."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal: str
    status: str
    progress: int
    parent_requirement_key: str | None = None


class CaseDetail(CaseOut):
    steps: list[StepOut] = []
    documents: list[DocumentOut] = []
    citations: list[CitationOut] = []
    # Flat, not nested CaseDetail — a sub-goal's own sub-goals are fetched by
    # opening it, so the response stays a fixed depth.
    sub_goals: list[SubGoalOut] = []
    parent: ParentRef | None = None
