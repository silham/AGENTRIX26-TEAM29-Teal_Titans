"""Citizen self-declaration of requirements ("I have it" / undo).

We do not collect citizen documents, so a requirement is satisfied by the
citizen telling us they hold it. Confirming also completes the plan step whose
purpose was to obtain that item, matched through ``Step.fulfills``.

Nothing here commits — the calling endpoint owns the transaction so a sub-goal
cascade across several cases applies atomically.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Case, Document, Step
from app.repositories import steps as steps_repo
from app.repositories.documents import requirement_key

CONFIRMED = "confirmed"
MISSING = "missing"


def find_by_key(db: Session, *, case_id: str, key: str) -> Document | None:
    """The requirement row on ``case_id`` matching a normalised key."""
    for doc in db.scalars(select(Document).where(Document.case_id == str(case_id))):
        if requirement_key(doc) == key:
            return doc
    return None


def apply(db: Session, *, case: Case, document: Document, status: str) -> None:
    """Confirm (or un-confirm) a requirement and sync the step that obtains it.

    Confirming completes every outstanding step carrying this requirement's key;
    undoing returns those steps to pending. Either way the case is recomputed
    exactly once, which is what keeps steps BEFORE the affected one untouched —
    they are only ever re-labelled active/pending, never completed.

    A requirement with no matching step just changes status; that is not an error
    (custom LLM-generated plans carry no ``fulfills`` keys).
    """
    key = requirement_key(document)
    document.status = status
    if status == CONFIRMED:
        document.issues = []

    if not key:
        steps_repo.recompute(db, case_id=case.id)
        return

    fulfilling = list(
        db.scalars(select(Step).where(Step.case_id == case.id, Step.fulfills == key))
    )
    if status == CONFIRMED:
        new_status = "completed"
        matches = {s.id for s in fulfilling if s.status != "completed"}
    else:
        # Only revert steps this confirmation completed; leave anything the
        # citizen is part-way through alone.
        new_status = "pending"
        matches = {s.id for s in fulfilling if s.status == "completed"}

    if matches:
        steps_repo.set_steps_status(db, case_id=case.id, step_ids=matches, status=new_status)
    else:
        steps_repo.recompute(db, case_id=case.id)
