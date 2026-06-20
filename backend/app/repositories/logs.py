"""Owner: M2. agent_logs writer (audit/trust). Functional in the scaffold."""
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import AgentLog


def write_log(
    db: Session,
    *,
    case_id: UUID,
    agent: str,
    decision: str,
    reason: str | None = None,
    source_url: str | None = None,
    confidence: float | None = None,
) -> AgentLog:
    log = AgentLog(
        case_id=case_id,
        agent=agent,
        decision=decision,
        reason=reason,
        source_url=source_url,
        confidence=confidence,
    )
    db.add(log)
    db.commit()
    return log
