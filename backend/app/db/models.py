"""Owner: M1. SQLAlchemy models — the SHARED DATA CONTRACT.

Every member reads/writes these columns. Column names are frozen in the scaffold
commit; changes route through M1. `user_id` is the NextAuth user id (a string);
the NextAuth adapter on the frontend owns the actual `users` table, so we keep
`user_id` as an indexed string with no hard FK to avoid cross-service migration
coupling.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

EMBED_DIM = 768  # Gemini text-embedding-004


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="in_progress")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    current_step_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    steps: Mapped[list[Step]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="Step.ord"
    )
    documents: Mapped[list[Document]] = relationship(back_populates="case", cascade="all, delete-orphan")
    logs: Mapped[list[AgentLog]] = relationship(back_populates="case", cascade="all, delete-orphan")
    messages: Mapped[list[Message]] = relationship(back_populates="case", cascade="all, delete-orphan")


class Step(Base):
    __tablename__ = "steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    ord: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # pending | active | completed | locked | skipped
    status: Mapped[str] = mapped_column(String(16), default="pending")
    depends_on: Mapped[list] = mapped_column(JSONB, default=list)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    case: Mapped[Case] = relationship(back_populates="steps")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # missing | accepted | rejected | incomplete | needs_verification
    status: Mapped[str] = mapped_column(String(24), default="missing")
    issues: Mapped[list] = mapped_column(JSONB, default=list)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    case: Mapped[Case] = relationship(back_populates="documents")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    agent: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    case: Mapped[Case] = relationship(back_populates="logs")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant | system
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    case: Mapped[Case] = relationship(back_populates="messages")


class DocChunk(Base):
    """RAG corpus chunk (M3 writes via ingestion)."""

    __tablename__ = "doc_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIM), nullable=True)
