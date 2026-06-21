"""Owner: M3. Ingestion helpers + embeddings dimension. No DB, no API keys."""
from pathlib import Path

from app.llm import embeddings
from app.rag import ingest


def test_chunk_text_short_returns_single_chunk():
    assert ingest.chunk_text("short text") == ["short text"]


def test_chunk_text_long_overlaps_and_covers():
    text = "Sentence. " * 400  # ~4000 chars
    chunks = ingest.chunk_text(text, size=800, overlap=120)
    assert len(chunks) > 1
    assert all(len(c) <= 900 for c in chunks)  # ~size + boundary slack


def test_parse_corpus_file(tmp_path: Path):
    f = tmp_path / "doc.txt"
    f.write_text(
        "source_url: https://example.gov.lk/page\ntitle: Example Page\n\nThe body text here.",
        encoding="utf-8",
    )
    url, title, body = ingest.parse_corpus_file(f)
    assert url == "https://example.gov.lk/page"
    assert title == "Example Page"
    assert body == "The body text here."


def test_real_corpus_has_documents():
    files = list(ingest.CORPUS_DIR.glob("*.txt"))
    assert files, "expected seeded corpus documents"
    for f in files:
        url, _title, body = ingest.parse_corpus_file(f)
        assert url and url.startswith("http")
        assert body


def test_fit_dim_pads_and_truncates():
    assert len(embeddings._fit_dim([0.1, 0.2])) == embeddings.DIM
    assert len(embeddings._fit_dim([0.0] * (embeddings.DIM + 50))) == embeddings.DIM


def test_embed_empty_returns_empty():
    assert embeddings.embed([]) == []
