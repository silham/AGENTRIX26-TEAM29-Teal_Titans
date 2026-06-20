"""Owner: M2. Assemble the LangGraph agent graph.

Every node is imported here ALREADY (scaffold contract), so members never edit this
file when they implement their node — they just fill in their own nodes/<name>.py.

Graph topology:
  START → planner → knowledge → dependency → eligibility → checklist
        → [interrupt_before=document] → document → form → reminder → END

The interrupt before "document" pauses the run waiting for a document upload or
user answer.  Resuming re-enters at the document node with the updated state.

The PostgresSaver checkpointer (thread_id = case_id) is wired in `runner.py`
at graph-compile time so each HTTP request gets the same compiled graph object
but a distinct thread.
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


def build_graph(checkpointer=None):
    """Return a compiled StateGraph.  Pass a checkpointer for resumable sessions."""
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
    # After checklist the graph pauses (interrupt_before="document") waiting
    # for the user to upload files or answer questions.  Resume continues here.
    g.add_edge("checklist", "document")
    g.add_edge("document", "form")
    g.add_edge("form", "reminder")
    g.add_edge("reminder", END)

    compile_kwargs: dict = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
        # Pause before document so the frontend can show the checklist and
        # wait for uploads before proceeding to verification.
        compile_kwargs["interrupt_before"] = ["document"]

    return g.compile(**compile_kwargs)
