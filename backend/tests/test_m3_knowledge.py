"""Owner: M3. Knowledge node — requirements (rules) + citations (retrieval). No DB.

Retrieval is monkeypatched so the test runs without Postgres or API keys.
"""
from app.graph.nodes import knowledge as knowledge_mod


def test_knowledge_gathers_requirements_and_citations(monkeypatch):
    monkeypatch.setattr(
        knowledge_mod.retriever,
        "search",
        lambda query, k=4: [
            {
                "content": "A valid NIC is mandatory for a passport.",
                "source_url": "https://www.immigration.gov.lk/passport",
                "title": "Passport requirements",
                "score": 0.91,
            }
        ],
    )

    state = {
        "goal": "I lost my NIC and need a passport",
        "detected_services": ["passport_application"],
    }
    out = knowledge_mod.knowledge(state)

    assert "valid_nic" in out["requirements"]
    assert out["citations"], "expected at least one citation"
    # Every citation carries a working-looking source URL.
    for c in out["citations"]:
        assert c["source_url"].startswith("http")
    assert out["logs"][-1]["agent"] == "RAG Knowledge"


def test_knowledge_dedupes_citation_urls(monkeypatch):
    dup_url = "https://www.immigration.gov.lk/web/index.php?option=com_content&view=article&id=141&Itemid=186&lang=en"
    monkeypatch.setattr(
        knowledge_mod.retriever,
        "search",
        lambda query, k=4: [
            {"content": "x", "source_url": dup_url, "title": "dup", "score": 0.5}
        ],
    )
    state = {"goal": "passport", "detected_services": ["passport_application"]}
    out = knowledge_mod.knowledge(state)
    urls = [c["source_url"] for c in out["citations"]]
    assert len(urls) == len(set(urls)), "citation source URLs must be unique"


def test_knowledge_handles_no_services(monkeypatch):
    monkeypatch.setattr(knowledge_mod.retriever, "search", lambda query, k=4: [])
    out = knowledge_mod.knowledge({"goal": "", "detected_services": []})
    assert out["requirements"] == []
    assert out["citations"] == []


# ── M6: knowledge-base grounding ────────────────────────────────────────────


def test_knowledge_reuses_the_planners_passages(monkeypatch):
    """The planner already embedded the goal to ground its plan; re-running the
    same search here would double the embedding cost of every run."""
    def _boom(*_a, **_k):
        raise AssertionError("retriever.search must not be called when passages exist")

    monkeypatch.setattr(knowledge_mod.retriever, "search", _boom)

    out = knowledge_mod.knowledge({
        "goal": "widows pension",
        "detected_services": ["custom_procedure"],
        "custom_requirements": ["Death certificate"],
        "retrieved_passages": [{
            "content": "Applications go to the Department of Pensions.",
            "source_url": "https://pensions.gov.lk/wop",
            "title": "W&OP Circular",
            "document_id": "doc-1",
            "score": 0.82,
        }],
    })
    assert out["requirements"] == ["Death certificate"]
    assert [c["source_url"] for c in out["citations"]] == ["https://pensions.gov.lk/wop"]


def test_uploaded_document_without_a_source_url_is_still_cited(monkeypatch):
    """An admin may upload a circular they have no public URL for. Dropping it
    would make the document invisible despite being used."""
    monkeypatch.setattr(knowledge_mod.retriever, "search", lambda query, k=4: [])
    out = knowledge_mod.knowledge({
        "goal": "widows pension",
        "detected_services": [],
        "retrieved_passages": [{
            "content": "Internal circular text.",
            "source_url": None,
            "title": "Unpublished Circular 12/2024",
            "document_id": "doc-9",
            "score": 0.7,
        }],
    })
    assert len(out["citations"]) == 1
    assert out["citations"][0]["title"] == "Unpublished Circular 12/2024"
    assert out["citations"][0]["source_url"] is None


def test_citations_are_tagged_with_their_origin(monkeypatch):
    """The UI uses origin to separate verified procedure from supporting
    material — the hybrid-RAG trust boundary."""
    monkeypatch.setattr(
        knowledge_mod.retriever,
        "search",
        lambda query, k=4: [{
            "content": "supporting text",
            "source_url": "https://pensions.gov.lk/wop",
            "title": "W&OP",
            "document_id": "doc-1",
            "score": 0.8,
        }],
    )
    out = knowledge_mod.knowledge({
        "goal": "passport", "detected_services": ["passport_application"],
    })
    origins = {c["origin"] for c in out["citations"]}
    assert origins == {"rules", "uploaded_document"}
