"""
Phase 3 – Performance Indexes.

Revision: 003_phase3_indexes
Parent:   002_phase2

Changes
-------
Additive index-only migration — no schema changes, no data changes.

Indexes added (all idempotent via CREATE INDEX IF NOT EXISTS):
  1. job_descriptions(status)
     → Speeds up employer job list filtered by status and
       candidate job browsing (published only).

  2. job_descriptions(created_at DESC)
     → Speeds up the default ORDER BY created_at DESC used in
       employer/candidate job listings.

  3. job_descriptions(company_id, status)
     → Composite index for the common query pattern:
       "give me all published jobs for company X".

  4. applications(status)
     → Accelerates employer pipeline queries filtered by application status.

  5. users(role)
     → Speeds up admin/employer lookups by role.

Down
----
Drops all five indexes.
"""
from __future__ import annotations

from alembic import op

revision: str = "003_phase3"
down_revision: str | None = "002_phase2"
branch_labels: str | None = None
depends_on: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
def upgrade() -> None:
    # 1. job_descriptions(status) — fast status filter
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_job_descriptions_status
        ON job_descriptions (status)
    """)

    # 2. job_descriptions(created_at DESC) — default sort
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_job_descriptions_created_at
        ON job_descriptions (created_at DESC)
    """)

    # 3. job_descriptions(company_id, status) — composite for company job lists
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_job_descriptions_company_status
        ON job_descriptions (company_id, status)
    """)

    # 4. applications(status) — pipeline queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_applications_status
        ON applications (status)
    """)

    # 5. users(role) — role-based lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_users_role
        ON users (role)
    """)


# ─────────────────────────────────────────────────────────────────────────────
def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_role")
    op.execute("DROP INDEX IF EXISTS ix_applications_status")
    op.execute("DROP INDEX IF EXISTS ix_job_descriptions_company_status")
    op.execute("DROP INDEX IF EXISTS ix_job_descriptions_created_at")
    op.execute("DROP INDEX IF EXISTS ix_job_descriptions_status")
