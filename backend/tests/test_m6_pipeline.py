"""Owner: M6. Shared chunk -> embed -> store pipeline. In-memory SQLite, no API keys.

The embedding column degrades to Text on SQLite, so vectors are stored as their
repr — fine here: these tests are about row bookkeeping (provenance, ordering,
idempotency), not similarity.
"""
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, DocChunk, KnowledgeDocument
from app.llm import embeddings
from app.rag import pipeline
from app.rag.ingest import chunk_text

LONG_TEXT = "Sri Lankan government procedure step. " * 120  # forces several chunks


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    """Deterministic stand-in so no model download or API key is needed."""
    monkeypatch.setattr(
        pipeline,
        "embed_with_model",
        lambda texts: ([[0.1] * embeddings.DIM for _ in texts], "test-model@768"),
    )


def _make_doc(db, filename="guide.txt", source_url="https://pensions.gov.lk/wop"):
    doc = KnowledgeDocument(
        id=filename, filename=filename, title="Guide", source_url=source_url, uploaded_by="t@x.lk"
    )
    db.add(doc)
    db.commit()
    return doc


def test_stores_chunks_with_ordering_and_provenance(db):
    doc = _make_doc(db)
    count, model_id = pipeline.store_document_chunks(
        db, document_id=doc.id, source_url=doc.source_url, title=doc.title, text=LONG_TEXT
    )
    db.commit()

    assert count > 1
    assert model_id == "test-model@768"
    chunks = list(db.scalars(select(DocChunk).order_by(DocChunk.chunk_index)))
    assert [c.chunk_index for c in chunks] == list(range(count))
    assert all(c.document_id == doc.id for c in chunks)
    assert all(c.embedding_model == "test-model@768" for c in chunks)


def test_reingest_replaces_rather_than_duplicates(db):
    doc = _make_doc(db)
    for _ in range(3):
        pipeline.store_document_chunks(
            db, document_id=doc.id, source_url=doc.source_url, title=doc.title, text=LONG_TEXT
        )
        db.commit()
    total = db.execute(select(func.count()).select_from(DocChunk)).scalar_one()
    assert total == len(chunk_text(LONG_TEXT))


def test_sweeps_legacy_chunks_that_share_a_source_url(db):
    """Chunks ingested before knowledge_documents existed have document_id NULL.
    Without this sweep the first post-migration ingest silently doubles the
    corpus, and nothing can delete the unparented copies afterwards."""
    doc = _make_doc(db)
    db.add(DocChunk(source_url=doc.source_url, title="old", content="legacy", document_id=None))
    db.commit()

    pipeline.store_document_chunks(
        db, document_id=doc.id, source_url=doc.source_url, title=doc.title, text=LONG_TEXT
    )
    db.commit()

    orphans = db.execute(
        select(func.count()).select_from(DocChunk).where(DocChunk.document_id.is_(None))
    ).scalar_one()
    assert orphans == 0


def test_empty_text_writes_nothing(db):
    doc = _make_doc(db)
    count, _ = pipeline.store_document_chunks(
        db, document_id=doc.id, source_url=doc.source_url, title=doc.title, text="   "
    )
    assert count == 0
