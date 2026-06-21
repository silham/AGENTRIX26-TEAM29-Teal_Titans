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
