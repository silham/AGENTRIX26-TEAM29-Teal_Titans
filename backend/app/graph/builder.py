"""Owner: M2. Assemble the LangGraph agent graph.

Every node is imported here ALREADY (scaffold contract), so members never edit this
file when they implement their node — they just fill in their own nodes/<name>.py.
LangGraph is imported lazily inside build_graph() to keep app startup light.
"""
from app.graph.nodes.checklist import checklist
from app.graph.nodes.dependency import dependency
from app.graph.nodes.document import document
from app.graph.nodes.eligibility import eligibility
from app.graph.nodes.form import form
from app.graph.nodes.knowledge import knowledge
from app.graph.nodes.planner import planner
from app.graph.nodes.reminder import reminder
from app.graph.state import GraphState

_graph = None


def build_graph():
    from langgraph.graph import END, START, StateGraph

    g = StateGraph(GraphState)
    g.add_node("planner", planner)
    g.add_node("knowledge", knowledge)
    g.add_node("dependency", dependency)
    g.add_node("eligibility", eligibility)
    g.add_node("checklist", checklist)
    g.add_node("document", document)
    g.add_node("form", form)
    g.add_node("reminder", reminder)

    g.add_edge(START, "planner")
    g.add_edge("planner", "knowledge")
    g.add_edge("knowledge", "dependency")
    g.add_edge("dependency", "eligibility")
    g.add_edge("eligibility", "checklist")
    g.add_edge("checklist", "reminder")
    g.add_edge("reminder", END)

    # TODO(M2): conditional edges for document/form, interrupt() for uploads/answers,
    #           and a PostgresSaver checkpointer (thread_id = case_id) for resumable runs.
    return g.compile()


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
