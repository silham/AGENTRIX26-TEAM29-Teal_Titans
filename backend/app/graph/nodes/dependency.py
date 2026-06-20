"""Owner: M3. Dependency node — build graph from JSON rules, lock blocked steps."""
from app.graph.state import GraphState


def dependency(state: GraphState) -> dict:
    # TODO(M3): from rules depends_on, compute order and lock blocked steps with a
    #           reason (e.g. "Valid NIC required"); return {"dependency_graph": {...}}.
    return {}
