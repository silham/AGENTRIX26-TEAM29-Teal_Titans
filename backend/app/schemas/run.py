"""Owner: M2. SSE event shape consumed by the frontend animation. SHARED CONTRACT."""
from typing import Any

from pydantic import BaseModel


class RunEvent(BaseModel):
    """One server-sent event per node execution."""

    agent: str               # "planner" | "knowledge" | "dependency" | ...
    status: str              # "started" | "completed" | "error"
    message: str | None = None
    payload: dict[str, Any] | None = None

    def to_sse(self) -> str:
        return f"data: {self.model_dump_json()}\n\n"
