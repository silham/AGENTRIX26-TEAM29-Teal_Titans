"""Owner: M2. Stream graph execution as SSE RunEvents.

The placeholder below keeps POST /cases/{id}/run working end-to-end before the
graph is wired. Replace with a real astream over get_graph().
"""
from collections.abc import AsyncGenerator

from app.graph.state import GraphState
from app.schemas.run import RunEvent

NODE_ORDER = ["planner", "knowledge", "dependency", "eligibility", "checklist", "reminder"]


async def run_case(
    case_id: str, user_id: str, goal: str, language: str = "en"
) -> AsyncGenerator[str, None]:
    state: GraphState = {
        "case_id": case_id,
        "user_id": user_id,
        "goal": goal,
        "language": language,
    }

    # TODO(M2): replace with
    #   async for event in get_graph().astream(state, config={"configurable": {"thread_id": case_id}}):
    #       yield RunEvent(...).to_sse()
    for node in NODE_ORDER:
        yield RunEvent(agent=node, status="started").to_sse()
        yield RunEvent(agent=node, status="completed", message="scaffold").to_sse()
