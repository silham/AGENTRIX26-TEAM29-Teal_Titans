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

EMBED_DIM = 768  # Gemini text-embedding-004


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
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    steps: Mapped[list[Step]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="Step.ord"
    )
    documents: Mapped[list[Document]] = relationship(back_populates="case", cascade="all, delete-orphan")
    logs: Mapped[list[AgentLog]] = relationship(back_populates="case", cascade="all, delete-orphan")
    messages: Mapped[list[Message]] = relationship(back_populates="case", cascade="all, delete-orphan")


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


class DocChunk(Base):
    """RAG corpus chunk (written via ingestion).

    Embedding is a real pgvector column on Postgres (enables cosine_distance
    search in retriever.py); on SQLite it degrades to Text and the retriever
    returns [] gracefully.
    """

    __tablename__ = "doc_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(EMBED_DIM).with_variant(Text, "sqlite"), nullable=True)
