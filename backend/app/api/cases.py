"""Owner: M1. Case CRUD + list + continue-later."""
from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from fastapi import Response

from app.auth.jwt import CurrentUser, get_current_user
from app.db.session import get_db
from app.rag import rules
from app.repositories import cases as repo
from app.repositories import documents as doc_repo
from app.repositories import requirements as req_repo
from app.repositories import steps as steps_repo
from app.repositories import subgoals as subgoal_repo
from app.schemas.case import (
    CaseCreate,
    CaseDetail,
    CaseOut,
    RequirementStatusUpdate,
    StepStatusUpdate,
)

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseOut, status_code=201)
def create_case(
    body: CaseCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    return repo.create_case(db, user_id=user.id, goal=body.goal, language=body.language)


@router.get("", response_model=list[CaseDetail])
def list_cases(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    # CaseDetail (with steps) so the dashboard can show each case's next step.
    return repo.list_cases(db, user_id=user.id)


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(
    case_id: UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    case = repo.get_case(db, case_id=case_id, user_id=user.id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.delete("/{case_id}", status_code=204)
def delete_case(
    case_id: UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    if not repo.delete_case(db, case_id=case_id, user_id=user.id):
        raise HTTPException(status_code=404, detail="Case not found")


@router.patch("/{case_id}/steps/{step_id}", response_model=CaseDetail)
def update_step_status(
    case_id: UUID,
    step_id: UUID,
    body: StepStatusUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Mark a step completed (or undo it); returns the recomputed case."""
    case = repo.get_case(db, case_id=case_id, user_id=user.id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    step = steps_repo.set_step_status(db, case_id=case_id, step_id=step_id, status=body.status)
    if step is None:
        raise HTTPException(status_code=404, detail="Step not found")

    # Finishing the last step of a sub-goal ticks the requirement it was
    # created for on the parent, and so on up the chain.
    if subgoal_repo.propagate_completion(db, case_id=str(case_id)):
        db.commit()

    db.refresh(case)
    return case


# ---------------------------------------------------------------------------
# Requirements — "I have it" / "How to get it?"
#
# We do not collect citizen documents, so a requirement is satisfied by the
# citizen saying they hold it, or by completing a sub-goal plan that obtains it.
# ---------------------------------------------------------------------------


def _get_requirement(db: Session, *, case_id: UUID, document_id: UUID):
    """Fetch a requirement row, ensuring it belongs to this case."""
    doc = doc_repo.get_document(db, document_id=document_id)
    if doc is None or doc.case_id != str(case_id):
        raise HTTPException(status_code=404, detail="Requirement not found")
    return doc


@router.patch("/{case_id}/requirements/{document_id}", response_model=CaseDetail)
def update_requirement_status(
    case_id: UUID,
    document_id: UUID,
    body: RequirementStatusUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Citizen declares they hold a requirement (or takes it back).

    Returns the whole recomputed case: confirming changes the requirement, the
    step that obtains it, the case progress and status, and which step is now
    active — so a narrower response would just force a second round trip.
    """
    case = repo.get_case(db, case_id=case_id, user_id=user.id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    doc = _get_requirement(db, case_id=case_id, document_id=document_id)
    req_repo.apply(db, case=case, document=doc, status=body.status)

    # Confirming the last outstanding requirement can finish the case, which may
    # in turn satisfy a requirement on ITS parent.
    subgoal_repo.propagate_completion(db, case_id=str(case_id))

    db.commit()
    db.refresh(case)
    return case


@router.post("/{case_id}/requirements/{document_id}/sub-goal", response_model=CaseDetail)
def create_requirement_sub_goal(
    case_id: UUID,
    document_id: UUID,
    response: Response,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Start a plan for obtaining this requirement, linked back to this case.

    201 when a new plan is created, 200 when an earlier one for the same
    requirement is reused — so a double click, or coming back a week later,
    lands the citizen on the plan they already have instead of a duplicate.
    """
    case = repo.get_case(db, case_id=case_id, user_id=user.id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    doc = _get_requirement(db, case_id=case_id, document_id=document_id)
    key = doc_repo.requirement_key(doc)
    if not key:
        raise HTTPException(status_code=422, detail="Requirement has no usable key.")

    existing = subgoal_repo.find_existing(
        db, user_id=user.id, parent_case_id=str(case_id), key=key
    )
    if existing is not None:
        response.status_code = 200
        return existing

    if len(subgoal_repo.ancestors(db, case_id=str(case_id))) >= subgoal_repo.MAX_CASCADE_DEPTH:
        raise HTTPException(
            status_code=409,
            detail="This plan is already nested too deeply to add another sub-goal.",
        )

    # Word the goal so the planner detects a real service where we model one;
    # otherwise fall back to the requirement's own display name.
    service = rules.service_for_requirement(key)
    goal = (
        f"I need to get my {rules.name(service)}"
        if service
        else f"I need to obtain my {doc.name}"
    )

    sub = repo.create_case(
        db,
        user_id=user.id,
        goal=goal,
        language=case.language,
        parent_case_id=str(case_id),
        parent_requirement_key=key,
    )
    response.status_code = 201
    return sub
