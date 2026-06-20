"""Owner: M2. POST /cases/{id}/run — streams the agent graph as SSE.

Query params:
  resume=true   Resume an interrupted run from its LangGraph checkpoint
                (used after a document upload or clarifying answer).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.jwt import CurrentUser, get_current_user
from app.db.session import get_db
from app.repositories.cases import get_case

router = APIRouter(prefix="/cases", tags=["run"])


@router.post("/{case_id}/run")
async def run_case_endpoint(
    case_id: UUID,
    resume: bool = False,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    case = get_case(db, case_id=case_id, user_id=user.id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    from app.graph.runner import run_case as _run

    return StreamingResponse(
        _run(str(case_id), user.id, case.goal, case.language, resume=resume),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
