"""Persist a plan's citations on the case row.

Citations previously existed only inside the SSE payload of a run, so a citizen
returning to their plan later saw no sources at all. The knowledge node now
writes them here.

Idempotent raw SQL for the same reason as 0001: create_all() coexists with
Alembic, so this may or may not already exist depending on which ran first.

Revision ID: 0002_case_citations
Revises: 0001_knowledge_base
"""
from __future__ import annotations

from alembic import op

revision = "0002_case_citations"
down_revision = "0001_knowledge_base"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE cases ADD COLUMN IF NOT EXISTS citations JSON DEFAULT '[]'::json")


def downgrade() -> None:
    op.execute("ALTER TABLE cases DROP COLUMN IF EXISTS citations")
