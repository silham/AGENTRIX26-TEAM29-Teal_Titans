"""Knowledge base: knowledge_documents table + doc_chunks provenance columns.

This is the first migration in the project. Everything before it was created by
``Base.metadata.create_all()`` at import time (app/db/session.py), which is kept
in place — it creates missing TABLES but never ALTERs existing ones, which is
exactly why the new doc_chunks columns need a migration.

Because both mechanisms are live, every statement here is idempotent raw SQL
(``IF NOT EXISTS`` / duplicate_object guard) rather than ``op.add_column``: on a
fresh database create_all() will already have made these objects by the time
``alembic upgrade head`` runs, and on the existing Neon database it will not
have. Both orders must succeed.

Postgres only. On SQLite the dev flow is create_all() alone.

Revision ID: 0001_knowledge_base
Revises:
"""
from __future__ import annotations

from alembic import op

revision = "0001_knowledge_base"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_documents (
            id                VARCHAR(36) PRIMARY KEY,
            filename          TEXT NOT NULL,
            title             TEXT,
            source_url        TEXT,
            storage_path      TEXT,
            mime              VARCHAR(128),
            size_bytes        INTEGER DEFAULT 0,
            page_count        INTEGER,
            char_count        INTEGER DEFAULT 0,
            chunk_count       INTEGER DEFAULT 0,
            extraction_method VARCHAR(32),
            embedding_model   VARCHAR(64),
            status            VARCHAR(16) NOT NULL DEFAULT 'pending',
            error             TEXT,
            uploaded_by       VARCHAR(255) NOT NULL,
            uploaded_at       TIMESTAMP DEFAULT now(),
            updated_at        TIMESTAMP DEFAULT now()
        )
        """
    )

    op.execute("ALTER TABLE doc_chunks ADD COLUMN IF NOT EXISTS document_id VARCHAR(36)")
    op.execute("ALTER TABLE doc_chunks ADD COLUMN IF NOT EXISTS chunk_index INTEGER DEFAULT 0")
    op.execute("ALTER TABLE doc_chunks ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(64)")
    op.execute("ALTER TABLE doc_chunks ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT now()")

    op.execute(
        """
        DO $$ BEGIN
            ALTER TABLE doc_chunks
                ADD CONSTRAINT doc_chunks_document_id_fkey
                FOREIGN KEY (document_id) REFERENCES knowledge_documents(id) ON DELETE CASCADE;
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_doc_chunks_document_id ON doc_chunks (document_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_doc_chunks_embedding_model ON doc_chunks (embedding_model)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_documents_status ON knowledge_documents (status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_documents_uploaded_by "
        "ON knowledge_documents (uploaded_by)"
    )

    # No ANN index on doc_chunks.embedding, deliberately. At the current scale
    # (low thousands of chunks) a sequential scan is single-digit milliseconds
    # and exact, while ivfflat's default lists=100 has poor recall below ~1000
    # rows and needs training data present when the index is built.
    #
    # Past roughly 10k chunks, add HNSW (no training data required, handles
    # incremental inserts):
    #
    #   CREATE INDEX CONCURRENTLY ix_doc_chunks_embedding_hnsw
    #       ON doc_chunks USING hnsw (embedding vector_cosine_ops)
    #       WITH (m = 16, ef_construction = 64);


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_doc_chunks_document_id")
    op.execute("DROP INDEX IF EXISTS ix_doc_chunks_embedding_model")
    op.execute("ALTER TABLE doc_chunks DROP CONSTRAINT IF EXISTS doc_chunks_document_id_fkey")
    op.execute("ALTER TABLE doc_chunks DROP COLUMN IF EXISTS document_id")
    op.execute("ALTER TABLE doc_chunks DROP COLUMN IF EXISTS chunk_index")
    op.execute("ALTER TABLE doc_chunks DROP COLUMN IF EXISTS embedding_model")
    op.execute("ALTER TABLE doc_chunks DROP COLUMN IF EXISTS created_at")
    op.execute("DROP TABLE IF EXISTS knowledge_documents")
