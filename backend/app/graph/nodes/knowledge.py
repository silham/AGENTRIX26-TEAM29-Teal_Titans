"""Owner: M3. RAG Knowledge node — requirements (rules) + citations (retrieval).

For each detected service it gathers the deterministic requirement list from the
JSON rules layer and supporting passages from the embedding retriever, then writes
``requirements`` and ``citations`` into GraphState. Verified facts (requirements,
source URLs) come from rules; narrative passages come from retrieval — kept
separate per the hybrid-RAG trust rule.
"""
from __future__ import annotations

from app.graph.nodes.audit import audit
from app.graph.state import GraphState
from app.rag import retriever, rules


def knowledge(state: GraphState) -> dict:
    services = state.get("detected_services") or []
    goal = state.get("goal", "")

    # 1) Deterministic requirements from the rules layer (union across services).
    requirements: list[str] = []
    for service in services:
        for req in rules.requirements(service):
            if req not in requirements:
                requirements.append(req)

    # 2) Citations: each service's canonical source + retrieved supporting passages.
    citations: list[dict] = []
    seen_urls: set[str] = set()

    def add_citation(title: str | None, url: str | None, snippet: str | None = None) -> None:
        if not url or url in seen_urls:
            return
        seen_urls.add(url)
        citation = {"title": title or url, "source_url": url}
        if snippet:
            citation["snippet"] = snippet
        citations.append(citation)

    for service in services:
        add_citation(rules.name(service), rules.source_url(service))

    # Retrieval over the goal (and service names) for narrative citations.
    query = goal or " ".join(rules.name(s) for s in services)
    for passage in retriever.search(query, k=4):
        snippet = (passage.get("content") or "")[:280]
        add_citation(passage.get("title"), passage.get("source_url"), snippet)

    log = audit(
        state,
        agent="RAG Knowledge",
        decision=f"Gathered {len(requirements)} requirement(s) and {len(citations)} citation(s) "
        f"for {len(services)} service(s).",
        reason="Requirements from deterministic rules; citations from official sources + retrieval.",
        source_url=citations[0]["source_url"] if citations else None,
        confidence=0.9 if citations else 0.5,
    )

    return {"requirements": requirements, "citations": citations, **log}
