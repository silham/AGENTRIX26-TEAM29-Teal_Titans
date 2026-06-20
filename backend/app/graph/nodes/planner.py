"""Owner: M2. Planner node — goal → detected services + intent (Groq)."""
from app.graph.state import GraphState


def planner(state: GraphState) -> dict:
    # TODO(M2): call app.llm.groq_client.chat(...) in JSON mode to detect services
    #           from state["goal"]; return {"detected_services": [...], "intent": {...}}.
    return {}
