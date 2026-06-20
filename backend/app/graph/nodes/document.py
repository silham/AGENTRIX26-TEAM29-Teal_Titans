"""Owner: M5. Document Verification node — Gemini Vision / Tesseract."""
from app.graph.state import GraphState


def document(state: GraphState) -> dict:
    # TODO(M5): verify uploaded docs (app.llm.gemini_vision / app.documents.ocr)
    #           → update each document's status + issues; return {"documents": [...]}.
    return {}
