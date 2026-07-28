"""Translation cache + normalised English goal.

Two things land together because they are the two halves of the same feature:
`translations` carries citizen-facing text OUT of English, and `cases.goal_en`
carries citizen input INTO English.

Idempotent raw SQL for the same reason as 0001-0003: create_all() runs at
import and coexists with Alembic, so either may have run first.

Revision ID: 0004_translations
Revises: 0003_requirements_and_subgoals
"""
from __future__ import annotations

from alembic import op

revision = "0004_translations"
down_revision = "0003_requirements_and_subgoals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # prompt_version is IN the primary key: it is what allows an improved
    # prompt or glossary to supersede earlier machine output instead of being
    # permanently shadowed by it.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS translations (
            source_hash     VARCHAR(64) NOT NULL,
            lang            VARCHAR(8)  NOT NULL,
            prompt_version  SMALLINT    NOT NULL DEFAULT 1,
            source_text     TEXT        NOT NULL,
            translated_text TEXT        NOT NULL,
            source          VARCHAR(8)  NOT NULL DEFAULT 'machine',
            created_at      TIMESTAMP   DEFAULT now(),
            PRIMARY KEY (source_hash, lang, prompt_version)
        )
        """
    )
    # Lets the seed/review tooling list every machine row awaiting review
    # without scanning the whole table.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_translations_lang_source "
        "ON translations (lang, source)"
    )

    op.execute("ALTER TABLE cases ADD COLUMN IF NOT EXISTS goal_en TEXT")
    op.execute(
        "ALTER TABLE cases ADD COLUMN IF NOT EXISTS "
        "goal_source VARCHAR(16) DEFAULT 'citizen'"
    )
    # Existing rows predate normalisation and are English by construction (the
    # UI only ever sent English goals), so seeding goal_en from goal keeps
    # `case.goal_en or case.goal` reading the same value either way.
    op.execute("UPDATE cases SET goal_en = goal WHERE goal_en IS NULL")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_translations_lang_source")
    op.execute("DROP TABLE IF EXISTS translations")
    op.execute("ALTER TABLE cases DROP COLUMN IF EXISTS goal_en")
    op.execute("ALTER TABLE cases DROP COLUMN IF EXISTS goal_source")
