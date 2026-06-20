"""Owner: M5. Document DTOs. TODO(M5): flesh out."""
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: str | None = None
    status: str
    issues: list = []
