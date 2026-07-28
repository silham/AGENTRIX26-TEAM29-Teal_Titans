"""Owner: M1. SQLAlchemy models — the SHARED DATA CONTRACT.

Rewritten to use SQLite-compatible types so the demo works without PostgreSQL.
When a real Postgres+pgvector deployment is wired up, swap String(36) back to
UUID(as_uuid=True) and JSON back to JSONB.

UUID primary keys are stored as String(36); Python helpers always convert UUID
objects to str before querying so drivers don't need dialect-specific handling.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

EMBED_DIM = 768  # gemini-embedding-001 at output_dimensionality=768


class Base(DeclarativeBase):
    pass


def _uuid_str() -> str:
    return str(uuid.uuid4())


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="in_progress")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    current_step_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en")

    # Sub-goal link: this case exists to obtain one requirement of another case
    # (created by "How to get it?" on the parent's Requirements tab).
    #
    # SET NULL, not CASCADE: deleting a passport plan must not destroy the
    # citizen's separate NIC plan, which stands on its own.
    parent_case_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # The normalised requirement key this sub-goal obtains — NOT a documents FK.
    # _sync_documents deletes and recreates 'missing' rows with fresh UUIDs on
    # every graph re-run, so a row reference would dangle; the key is stable.
    # Same spelling as Document.type and Step.fulfills.
    parent_requirement_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Sources behind this plan, written by the knowledge node. Persisted rather
    # than left in the SSE payload so the citizen still sees them when they come
    # back to the plan days later. Each entry: {title, source_url, origin, snippet?}
    citations: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    steps: Mapped[list[Step]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="Step.ord"
    )
    documents: Mapped[list[Document]] = relationship(back_populates="case", cascade="all, delete-orphan")
    logs: Mapped[list[AgentLog]] = relationship(back_populates="case", cascade="all, delete-orphan")
    messages: Mapped[list[Message]] = relationship(back_populates="case", cascade="all, delete-orphan")

    # Deliberately NO cascade="all, delete-orphan" here, unlike the children
    # above: a sub-goal is a plan in its own right and outlives its parent.
    parent: Mapped[Case | None] = relationship(
        "Case", remote_side=[id], back_populates="sub_goals"
    )
    sub_goals: Mapped[list[Case]] = relationship(back_populates="parent")


class Step(Base):
    __tablename__ = "steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    ord: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # pending | active | completed | locked | skipped
    status: Mapped[str] = mapped_column(String(16), default="pending")
    depends_on: Mapped[list] = mapped_column(JSON, default=list)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Requirement key this step exists to obtain, e.g. "police_report". Lets
    # "I have it" on the Requirements tab complete the step that gets that item.
    # Width mirrors Document.type — they hold the same normalised key.
    fulfills: Mapped[str | None] = mapped_column(String(64), nullable=True)

    case: Mapped[Case] = relationship(back_populates="steps")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # missing | accepted | rejected | incomplete | needs_verification
    status: Mapped[str] = mapped_column(String(24), default="missing")
    issues: Mapped[list] = mapped_column(JSON, default=list)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    case: Mapped[Case] = relationship(back_populates="documents")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    agent: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    case: Mapped[Case] = relationship(back_populates="logs")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    case_id: Mapped[str] = mapped_column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant | system
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    case: Mapped[Case] = relationship(back_populates="messages")


class KnowledgeDocument(Base):
    """A government document backing the RAG knowledge base.

    Created either by an admin upload (POST /admin/knowledge) or by the corpus
    CLI (`python -m app.rag.ingest`, uploaded_by="corpus-cli"), so both sources
    are listed, reindexed and deleted through the same admin surface.
    """

    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    filename: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    # text | pdf_text | pdf_ocr | pdf_embedded_image_ocr | docx | image_ocr
    extraction_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # pending | processing | ready | failed
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[str] = mapped_column(String(255), index=True)  # admin email
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    chunks: Mapped[list[DocChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocChunk(Base):
    """RAG corpus chunk (written via ingestion).

    Embedding is a real pgvector column on Postgres (enables cosine_distance
    search in retriever.py); on SQLite it degrades to Text and the retriever
    short-circuits to [] with a warning.

    ``embedding_model`` records which model produced the vector. This matters:
    the local fallback is 384-dim zero-padded to 768, which is NOT in the same
    vector space as Gemini's 768 — mixing them silently produces meaningless
    rankings, so the retriever filters on this column.
    """

    __tablename__ = "doc_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    # Nullable so chunks ingested before the knowledge-base feature survive.
    document_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(EMBED_DIM).with_variant(Text, "sqlite"), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    document: Mapped[KnowledgeDocument | None] = relationship(back_populates="chunks")
