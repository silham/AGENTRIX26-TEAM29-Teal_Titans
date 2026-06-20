"""Owner: M2. POST /cases/{id}/run — streams the agent graph as SSE.
LangGraph is imported lazily (inside the handler) so app startup needs no heavy deps."""
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth.jwt import CurrentUser, get_current_user

router = APIRouter(prefix="/cases", tags=["run"])


@router.post("/{case_id}/run")
async def run_case(
    case_id: UUID,
    goal: str = "",
    user: CurrentUser = Depends(get_current_user),
):
    from app.graph.runner import run_case as _run  # lazy import

    return StreamingResponse(
        _run(str(case_id), user.id, goal),
        media_type="text/event-stream",
    )
