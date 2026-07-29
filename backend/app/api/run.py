"""POST /cases/{id}/run — streams the agent graph as SSE.

Query params:
  resume=true   Resume an interrupted run from its LangGraph checkpoint
                (after a document upload or eligibility answers).

Optional JSON body:
  {"answers": {"citizenship": "sri_lankan", "age": 30, ...}}
                Citizen's answers to the eligibility questions; injected into
                graph state before resuming.
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.jwt import CurrentUser, get_current_user
from app.db.session import get_db
from app.i18n.deps import request_language
from app.i18n.understand import normalize_input_async
from app.repositories.cases import get_case

router = APIRouter(prefix="/cases", tags=["run"])


class RunBody(BaseModel):
    answers: dict[str, Any] | None = None


async def _normalize_answers(
    answers: dict[str, Any] | None, question_fields: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Translate free-text eligibility answers to English, and ONLY those.

    This restriction is load-bearing. `_check_rule` compares answer values with
    exact `==` against English rule values from the procedure JSON, and choice
    options carry the machine key as their `value`. Normalising a choice answer
    would rewrite "sri_lankan" into a sentence and silently make an eligible
    citizen ineligible. Booleans and numbers are not text at all.

    So: a value is normalised only when the question that produced it is
    declared `type == "text"`.
    """
    if not answers:
        return answers

    text_fields = {
        spec.get("field")
        for spec in question_fields
        if isinstance(spec, dict) and spec.get("type") == "text"
    }
    if not text_fields:
        return answers

    out = dict(answers)
    for field, value in answers.items():
        if field in text_fields and isinstance(value, str) and value.strip():
            out[field] = (await normalize_input_async(value)).english
    return out


@router.post("/{case_id}/run")
async def run_case_endpoint(
    case_id: UUID,
    resume: bool = False,
    body: RunBody | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    lang: str = Depends(request_language),
):
    case = get_case(db, case_id=case_id, user_id=user.id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    from app.graph.runner import pending_question_fields, run_case as _run

    answers = body.answers if body else None
    if resume and answers:
        answers = await _normalize_answers(
            answers, await pending_question_fields(str(case_id))
        )

    return StreamingResponse(
        _run(
            str(case_id),
            user.id,
            # goal_en, not goal: the graph, the planner's English keyword
            # fallback and the English RAG corpus all need English. `goal`
            # holds the citizen's original wording for display only.
            case.goal_en or case.goal,
            lang,
            resume=resume,
            answers=answers,
        ),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
