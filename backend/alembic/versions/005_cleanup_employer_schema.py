"""
alembic/versions/005_cleanup_employer_schema.py
================================================
Phase 5 — Candidate-Only Platform Cleanup.

Removes all employer-specific schema objects:
  - DROP TABLE applications
  - DROP TABLE companies
  - DROP TYPE application_status_enum
  - DROP COLUMN users.role (all users are candidates now)
  - DROP COLUMN job_descriptions.status (all crawled jobs are active)
  - DROP COLUMN job_descriptions.company_id (no company ownership)
  - DROP COLUMN job_descriptions.applicant_count (no apply flow)
  - DROP COLUMN job_descriptions.deadline (not needed)
  - DROP INDEXES related to above columns

All operations are idempotent (IF EXISTS guards).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "005_candidate_platform"
down_revision: str = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Drop applications table ────────────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_applications_job_score")
    op.execute("DROP INDEX IF EXISTS ix_applications_match_score")
    op.execute("DROP INDEX IF EXISTS ix_applications_status")
    op.execute("DROP INDEX IF EXISTS ix_applications_candidate_id")
    op.execute("DROP INDEX IF EXISTS ix_applications_job_id")
    op.execute("DROP TABLE IF EXISTS applications CASCADE")

    # ── 2. Drop ENUM type ─────────────────────────────────────────────────────
    op.execute("DROP TYPE IF EXISTS application_status_enum CASCADE")

    # ── 3. Drop companies table ───────────────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_companies_owner_id")
    op.execute("DROP TABLE IF EXISTS companies CASCADE")

    # ── 4. Drop employer-specific columns from users ──────────────────────────
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='role'
            ) THEN
                ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_role;
                ALTER TABLE users DROP COLUMN IF EXISTS role;
            END IF;
        END $$;
    """)

    # ── 5. Drop employer-specific columns from job_descriptions ──────────────
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='job_descriptions' AND column_name='status'
            ) THEN
                ALTER TABLE job_descriptions DROP CONSTRAINT IF EXISTS ck_job_status;
                ALTER TABLE job_descriptions DROP COLUMN IF EXISTS status;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='job_descriptions' AND column_name='company_id'
            ) THEN
                ALTER TABLE job_descriptions DROP CONSTRAINT IF EXISTS fk_job_company;
                DROP INDEX IF EXISTS ix_job_descriptions_company_id;
                DROP INDEX IF EXISTS ix_job_descriptions_company_status;
                ALTER TABLE job_descriptions DROP COLUMN IF EXISTS company_id;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='job_descriptions' AND column_name='applicant_count'
            ) THEN
                ALTER TABLE job_descriptions DROP COLUMN IF EXISTS applicant_count;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='job_descriptions' AND column_name='deadline'
            ) THEN
                ALTER TABLE job_descriptions DROP COLUMN IF EXISTS deadline;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Intentionally minimal — restoring employer schema would require
    # a full Phase 1 re-run which is not safe without data backup.
    pass
