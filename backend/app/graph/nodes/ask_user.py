"""Human-in-the-loop pause point for eligibility questions.

The graph is compiled with ``interrupt_before=["ask_user"]``: when the
eligibility node needs facts it routes here, the run pauses, and the frontend
shows the questions. The answer flow (``POST /cases/{id}/run?resume=true`` with
an ``answers`` body) writes the citizen's answers into ``state["facts"]`` via
``graph.aupdate_state(..., as_node="ask_user")`` — so this node body never
actually executes on that path; it exists as a named target for the interrupt
and the state update.
"""
from app.graph.state import GraphState


def ask_user(state: GraphState) -> dict:
    return {}
