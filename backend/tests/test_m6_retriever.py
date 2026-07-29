"""Owner: M6. Retriever hardening: dialect guard, score threshold, model filter.

No Postgres — the point of most of these is precisely what happens WITHOUT it.
"""
from types import SimpleNamespace

from app.config import settings
from app.rag import retriever


class _FakeDialect:
    def __init__(self, name):
        self.name = name


def _use_dialect(monkeypatch, name):
    monkeypatch.setattr(retriever, "engine", SimpleNamespace(dialect=_FakeDialect(name)))
    # These are one-shot log guards; reset so each test exercises the real path.
    monkeypatch.setattr(retriever, "_warned_dialect", False)
    monkeypatch.setattr(retriever, "_warned_unstamped", False)


def test_empty_query_returns_nothing():
    assert retriever.search("   ") == []


def test_non_postgres_short_circuits_without_raising(monkeypatch, caplog):
    """On SQLite, cosine_distance emits invalid SQL. It must be reported, not
    swallowed into an indistinguishable "corpus is empty"."""
    _use_dialect(monkeypatch, "sqlite")
    with caplog.at_level("WARNING"):
        assert retriever.search("passport requirements") == []
    assert any("sqlite" in r.message.lower() or "sqlite" in str(r.args) for r in caplog.records)


def test_health_reports_the_dialect_problem_instead_of_raising(monkeypatch):
    _use_dialect(monkeypatch, "sqlite")
    info = retriever.health()
    assert info["ok"] is False
    assert "pgvector" in info["error"]


def test_embedding_failure_degrades_to_empty(monkeypatch):
    _use_dialect(monkeypatch, "postgresql")
    monkeypatch.setattr(
        retriever,
        "embed_query_with_model",
        lambda _t: (_ for _ in ()).throw(RuntimeError("no api key")),
    )
    assert retriever.search("passport") == []


def _fake_rows(monkeypatch, rows):
    """Stand in for the DB round-trip, returning row-like objects."""
    _use_dialect(monkeypatch, "postgresql")
    monkeypatch.setattr(retriever, "embed_query_with_model", lambda _t: ([0.0], "model-a"))

    class _Session:
        def __enter__(self): return self
        def __exit__(self, *_a): return False
        def execute(self, _stmt): return SimpleNamespace(all=lambda: rows)

    monkeypatch.setattr(retriever, "SessionLocal", _Session)


def test_low_scoring_rows_are_filtered_out(monkeypatch):
    rows = [
        SimpleNamespace(content="close", source_url="u1", title="t1", document_id="d",
                        chunk_index=0, distance=0.1),   # score 0.9
        SimpleNamespace(content="far", source_url="u2", title="t2", document_id="d",
                        chunk_index=1, distance=0.95),  # score 0.05
    ]
    _fake_rows(monkeypatch, rows)
    hits = retriever.search("q", k=5, min_score=0.5)
    assert [h["content"] for h in hits] == ["close"]


def test_rag_min_score_override_is_honoured(monkeypatch):
    monkeypatch.setattr(settings, "rag_min_score", 0.8)
    rows = [
        SimpleNamespace(content="borderline", source_url="u", title="t", document_id="d",
                        chunk_index=0, distance=0.25),  # score 0.75, below the override
    ]
    _fake_rows(monkeypatch, rows)
    assert retriever.search("q", k=5) == []


def test_threshold_falls_back_to_the_per_model_default(monkeypatch):
    """Gemini and the local fallback produce incompatible score scales, so with
    no explicit override the floor must come from the model that embedded the
    query — a single global number would either admit noise or reject everything."""
    monkeypatch.setattr(settings, "rag_min_score", None)
    monkeypatch.setattr(
        retriever, "default_min_score", lambda model_id: 0.9 if model_id == "model-a" else 0.0
    )
    rows = [
        SimpleNamespace(content="mid", source_url="u", title="t", document_id="d",
                        chunk_index=0, distance=0.3),  # score 0.70 < 0.9
    ]
    _fake_rows(monkeypatch, rows)  # this stub reports the query model as "model-a"
    assert retriever.search("q", k=5) == []


def test_results_carry_provenance(monkeypatch):
    rows = [
        SimpleNamespace(content="c", source_url="u", title="t", document_id="doc-1",
                        chunk_index=3, distance=0.05),
    ]
    _fake_rows(monkeypatch, rows)
    hit = retriever.search("q", k=1)[0]
    assert hit["document_id"] == "doc-1"
    assert hit["chunk_index"] == 3
    assert hit["score"] == 0.95


def test_k_is_respected_after_filtering(monkeypatch):
    rows = [
        SimpleNamespace(content=f"c{i}", source_url=f"u{i}", title="t", document_id="d",
                        chunk_index=i, distance=0.05)
        for i in range(9)
    ]
    _fake_rows(monkeypatch, rows)
    assert len(retriever.search("q", k=2)) == 2
