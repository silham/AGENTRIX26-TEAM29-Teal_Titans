"""Requirements tab: step->requirement link, and sub-goal parentage on cases.

``steps.fulfills`` records which requirement a step exists to obtain. The value
was already computed by ``compose_checklist`` but discarded at the persistence
boundary, so nothing downstream could act on it; "I have it" needs it to know
which step to complete.

``cases.parent_case_id`` / ``cases.parent_requirement_key`` record that a case
was spawned from a requirement on another case ("How to get it?"), so finishing
the sub-goal can tick that requirement on the parent.

Idempotent raw SQL for the same reason as 0001/0002: ``create_all()`` runs at
import and may already have made these on a fresh database, while on an existing
one it cannot (it never ALTERs). Both orders must succeed.

Revision ID: 0003_requirements_and_subgoals
Revises: 0002_case_citations
"""
from __future__ import annotations

from alembic import op

revision = "0003_requirements_and_subgoals"
down_revision = "0002_case_citations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE steps ADD COLUMN IF NOT EXISTS fulfills VARCHAR(64)")

    op.execute("ALTER TABLE cases ADD COLUMN IF NOT EXISTS parent_case_id VARCHAR(36)")
    op.execute("ALTER TABLE cases ADD COLUMN IF NOT EXISTS parent_requirement_key VARCHAR(64)")

    # ON DELETE SET NULL, not CASCADE: a sub-goal is a plan in its own right and
    # must survive its parent being deleted.
    op.execute(
        """
        DO $$ BEGIN
            ALTER TABLE cases
                ADD CONSTRAINT cases_parent_case_id_fkey
                FOREIGN KEY (parent_case_id) REFERENCES cases(id) ON DELETE SET NULL;
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_cases_parent_case_id ON cases (parent_case_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_cases_parent_case_id")
    op.execute("ALTER TABLE cases DROP CONSTRAINT IF EXISTS cases_parent_case_id_fkey")
    op.execute("ALTER TABLE cases DROP COLUMN IF EXISTS parent_requirement_key")
    op.execute("ALTER TABLE cases DROP COLUMN IF EXISTS parent_case_id")
    op.execute("ALTER TABLE steps DROP COLUMN IF EXISTS fulfills")
