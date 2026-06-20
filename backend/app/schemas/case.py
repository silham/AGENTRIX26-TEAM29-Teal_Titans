"""Owner: M1. Case/step DTOs."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CaseCreate(BaseModel):
    goal: str
    language: str = "en"


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


class CaseDetail(CaseOut):
    steps: list[StepOut] = []
