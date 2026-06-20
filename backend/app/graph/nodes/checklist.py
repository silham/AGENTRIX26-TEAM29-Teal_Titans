"""Owner: M4. Checklist node — ordered tasks + progress + next best action."""
from app.graph.state import GraphState


def checklist(state: GraphState) -> dict:
    # TODO(M4): combine requirements + dependency_graph + eligibility into an ordered
    #           checklist; persist via app.repositories.steps.replace_steps(...);
    #           return {"checklist": [...], "progress": int}.
    return {}
