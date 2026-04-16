"""
alembic/versions/004_add_match_score.py
========================================
Phase 4 — AI Ranking System.

Additive migration: adds match_score column to the applications table
and a supporting index for ORDER BY match_score DESC queries.

Idempotent: each step is wrapped in a column-exists check.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003_phase3"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """Return True if the column already exists (idempotency guard)."""
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return result.fetchone() is not None


def _index_exists(index_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname = :i"
        ),
        {"i": index_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    # ── 1. Add match_score column ─────────────────────────────────────────────
    if not _column_exists("applications", "match_score"):
        op.add_column(
            "applications",
            sa.Column("match_score", sa.Float(), nullable=True, comment="AI ranking score [0..1]"),
        )

    # ── 2. Index for fast ORDER BY match_score DESC ───────────────────────────
    if not _index_exists("ix_applications_match_score"):
        op.create_index(
            "ix_applications_match_score",
            "applications",
            ["match_score"],
            postgresql_where=sa.text("match_score IS NOT NULL"),
        )

    # ── 3. Composite index: (job_id, match_score DESC) for rank-candidates ────
    if not _index_exists("ix_applications_job_score"):
        op.create_index(
            "ix_applications_job_score",
            "applications",
            [sa.text("job_id"), sa.text("match_score DESC NULLS LAST")],
            postgresql_using="btree",
        )


def downgrade() -> None:
    op.drop_index("ix_applications_job_score",    table_name="applications", if_exists=True)
    op.drop_index("ix_applications_match_score",  table_name="applications", if_exists=True)
    op.drop_column("applications", "match_score")
