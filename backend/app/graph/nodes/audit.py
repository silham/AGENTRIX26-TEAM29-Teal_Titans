"""Owner: M2. Cross-cutting audit/trust helper. Nodes call audit() to log decisions
into state; the runner also persists them via app.repositories.logs.write_log."""
from app.graph.state import GraphState


def audit(
    state: GraphState,
    *,
    agent: str,
    decision: str,
    reason: str | None = None,
    source_url: str | None = None,
    confidence: float | None = None,
) -> dict:
    entry = {
        "agent": agent,
        "decision": decision,
        "reason": reason,
        "source_url": source_url,
        "confidence": confidence,
    }
    return {"logs": [*state.get("logs", []), entry]}
