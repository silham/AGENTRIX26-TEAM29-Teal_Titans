"""Owner: M3. RAG Knowledge node — requirements (rules) + citations (retrieval).

For each detected service it gathers the deterministic requirement list from the
JSON rules layer and supporting passages from the embedding retriever, then writes
``requirements`` and ``citations`` into GraphState. Verified facts (requirements,
source URLs) come from rules; narrative passages come from retrieval — kept
separate per the hybrid-RAG trust rule.

Each citation carries an ``origin``: "rules" for a service's canonical government
URL, "uploaded_document" for a passage retrieved from the admin knowledge base.
The UI uses that to show the citizen which claims are verified procedure and
which are supporting material.
"""
from __future__ import annotations

from app.config import settings
from app.graph.nodes.audit import audit
from app.graph.state import GraphState
from app.rag import retriever, rules


def _persist_citations(case_id: str | None, citations: list[dict]) -> None:
    """Save citations onto the Case row so they outlive the SSE run.

    Best-effort, matching the rest of the graph: a citizen must still get their
    plan if this write fails. Tests run this node without a DB.
    """
    if not case_id or not citations:
        return
    import sys

    from sqlalchemy import update

    from app.db.models import Case
    from app.db.session import SessionLocal

    try:
        with SessionLocal() as db:
            db.execute(update(Case).where(Case.id == str(case_id)).values(citations=citations))
            db.commit()
    except Exception as exc:  # noqa: BLE001 — never fail the run over a citation write
        print(f"[knowledge] could not persist citations for {case_id}: {exc!r}", file=sys.stderr)


def knowledge(state: GraphState) -> dict:
    services = state.get("detected_services") or []
    goal = state.get("goal", "")

    # 1) Requirements: rules layer for known services; custom_requirements for custom_procedure.
    #    Retrieval never contributes here — requirements must stay deterministic.
    requirements: list[str] = []
    for service in services:
        if service == "custom_procedure":
            for req in (state.get("custom_requirements") or []):
                if req not in requirements:
                    requirements.append(req)
        else:
            for req in rules.requirements(service):
                if req not in requirements:
                    requirements.append(req)

    # 2) Citations: each service's canonical source + retrieved supporting passages.
    citations: list[dict] = []
    seen_keys: set[str] = set()

    def add_citation(
        title: str | None,
        url: str | None,
        *,
        origin: str,
        snippet: str | None = None,
        score: float | None = None,
        document_id: str | None = None,
    ) -> None:
        # Dedupe on the URL when there is one, else on the document — an
        # uploaded document without a source_url is still worth citing by title.
        key = url or (f"doc:{document_id}" if document_id else "")
        if not key or key in seen_keys:
            return
        seen_keys.add(key)
        citation: dict = {"title": title or url or "Uploaded document", "source_url": url, "origin": origin}
        if snippet:
            citation["snippet"] = snippet
        if score is not None:
            citation["score"] = score
        citations.append(citation)

    for service in services:
        add_citation(rules.name(service), rules.source_url(service), origin="rules")

    # Reuse the planner's passages when it already retrieved them for grounding;
    # otherwise retrieve here. Saves a duplicate embed call per run.
    passages = state.get("retrieved_passages")
    if not passages:
        query = goal or " ".join(rules.name(s) for s in services)
        passages = retriever.search(query, k=settings.rag_top_k)

    for passage in passages:
        add_citation(
            passage.get("title"),
            passage.get("source_url"),
            origin="uploaded_document",
            snippet=(passage.get("content") or "")[:280],
            score=passage.get("score"),
            document_id=passage.get("document_id"),
        )

    _persist_citations(state.get("case_id"), citations)

    has_rules_citation = any(c["origin"] == "rules" for c in citations)
    confidence = 0.9 if has_rules_citation else 0.75 if citations else 0.5

    log = audit(
        state,
        agent="RAG Knowledge",
        decision=f"Gathered {len(requirements)} requirement(s) and {len(citations)} citation(s) "
        f"for {len(services)} service(s).",
        reason="Requirements from deterministic rules; citations from official sources + retrieval.",
        source_url=citations[0]["source_url"] if citations else None,
        confidence=confidence,
    )

    return {"requirements": requirements, "citations": citations, **log}
