"""Sub-goal parentage: spawning a plan from a requirement, and the completion
cascade back up to the parent.

A sub-goal is created by "How to get it?" on a parent's Requirements tab. It is
a full, independent plan (its own LangGraph thread, its own steps) that happens
to record which requirement of which case it exists to satisfy. When it finishes,
that requirement is ticked on the parent automatically.

Nothing here commits — the calling endpoint owns the transaction, so a cascade
spanning several cases applies atomically on one session.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Case
from app.repositories import requirements as req_repo
from app.schemas.document import SATISFIED_STATUSES

logger = logging.getLogger(__name__)

#: How deep a chain of sub-goals may run. Also bounds the completion cascade.
MAX_CASCADE_DEPTH = 5


def ancestors(db: Session, *, case_id: str, limit: int = MAX_CASCADE_DEPTH + 1) -> list[str]:
    """Case ids from ``case_id``'s parent upward. Stops on a cycle or ``limit``."""
    chain: list[str] = []
    seen = {str(case_id)}
    current = db.get(Case, str(case_id))
    while current is not None and current.parent_case_id and len(chain) < limit:
        parent_id = current.parent_case_id
        if parent_id in seen:
            break
        chain.append(parent_id)
        seen.add(parent_id)
        current = db.get(Case, parent_id)
    return chain


def find_existing(db: Session, *, user_id: str, parent_case_id: str, key: str) -> Case | None:
    """An earlier sub-goal for the same requirement, so a repeat click reuses it."""
    return db.scalars(
        select(Case)
        .where(
            Case.user_id == user_id,
            Case.parent_case_id == str(parent_case_id),
            Case.parent_requirement_key == key,
        )
        .order_by(Case.created_at.desc())
        .limit(1)
    ).first()


def propagate_completion(
    db: Session,
    *,
    case_id: str,
    _seen: set[str] | None = None,
    _depth: int = 0,
) -> list[str]:
    """If this case is now finished, tick the requirement it was created for.

    Recurses upward so a chain (grandparent <- parent <- this) settles in one
    pass. Returns the ids of the cases it updated. Safe to call unconditionally:
    it returns immediately unless the case is genuinely complete.

    Three guards, because a self-referential FK driving automated writes deserves
    more than one: ``_seen`` catches a cycle, ``_depth`` bounds a long chain, and
    the already-satisfied check below short-circuits the common repeat call
    before any recursion happens.
    """
    seen = _seen if _seen is not None else set()
    case_id = str(case_id)

    if case_id in seen or _depth >= MAX_CASCADE_DEPTH:
        logger.warning(
            "Sub-goal cascade stopped at %s (depth=%d, revisited=%s).",
            case_id, _depth, case_id in seen,
        )
        return []
    seen.add(case_id)

    case = db.get(Case, case_id)
    if case is None or case.status != "completed":
        return []
    if not case.parent_case_id or not case.parent_requirement_key:
        return []

    parent = db.get(Case, case.parent_case_id)
    if parent is None or parent.user_id != case.user_id:
        return []

    document = req_repo.find_by_key(
        db, case_id=parent.id, key=case.parent_requirement_key
    )
    # The requirement may have vanished from the parent's plan on a re-run.
    if document is None:
        return []
    if document.status in SATISFIED_STATUSES:
        return []

    req_repo.apply(db, case=parent, document=document, status=req_repo.CONFIRMED)
    logger.info(
        "Sub-goal %s complete -> confirmed '%s' on parent %s.",
        case_id, case.parent_requirement_key, parent.id,
    )

    return [parent.id] + propagate_completion(
        db, case_id=parent.id, _seen=seen, _depth=_depth + 1
    )
