"""
Phase 2 – Data Migration: user_interactions → applications.

Revision: 002_phase2_migrate
Parent:   001_phase1

Changes
-------
1. Copies every row from user_interactions WHERE action = 'applied' into
   the applications table:
     user_id        → candidate_id
     job_id         → job_id
     cv_id          → cv_id          (optional, may be NULL)
     created_at     → applied_at
     status         = 'applied'      (default starting status)

2. Ignores duplicates: if a (job_id, candidate_id) pair already exists in
   applications, the ON CONFLICT DO NOTHING clause silently skips it.

3. Recalculates applicant_count on job_descriptions from the applications
   table to ensure consistency after the backfill.

Down
----
The down migration is intentionally a no-op — deleting migrated application
rows is destructive and cannot be done safely without knowing which rows came
from this migration vs. newly submitted applications.

Notes
-----
* Pure SQL — no Python ORM objects — so this migration is safe to run
  even if models evolve later.
* ON CONFLICT DO NOTHING requires the UNIQUE constraint
  unique_application(job_id, candidate_id) from migration 001.
* gen_random_uuid() comes from pgcrypto (enabled in migration 001).
"""
from __future__ import annotations

from alembic import op

# revision identifiers
revision: str = "002_phase2"
down_revision: str | None = "001_phase1"
branch_labels: str | None = None
depends_on: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
def upgrade() -> None:
    # ── 1. Backfill applications from user_interactions ───────────────────────
    op.execute("""
        INSERT INTO applications (
            id,
            job_id,
            candidate_id,
            cv_id,
            status,
            cover_letter,
            note,
            applied_at,
            updated_at
        )
        SELECT
            gen_random_uuid(),          -- fresh PK for each migrated row
            ui.job_id,
            ui.user_id,                 -- user_id → candidate_id
            ui.cv_id,                   -- optional; NULL if not present
            'applied',                  -- starting status for all migrated rows
            NULL,                       -- no cover letter in legacy interactions
            NULL,                       -- no notes in legacy interactions
            ui.created_at,              -- preserve original application timestamp
            ui.created_at              -- updated_at = applied_at on creation
        FROM user_interactions ui
        WHERE ui.action = 'applied'
          -- Only migrate if the job and candidate still exist
          AND EXISTS (SELECT 1 FROM job_descriptions j WHERE j.id = ui.job_id)
          AND EXISTS (SELECT 1 FROM users u WHERE u.id = ui.user_id)
        ON CONFLICT (job_id, candidate_id) DO NOTHING
    """)

    # ── 2. Reconcile applicant_count on job_descriptions ─────────────────────
    # After the backfill the denormalized counter may be stale or zero.
    # Recalculate from the authoritative applications table.
    op.execute("""
        UPDATE job_descriptions jd
        SET applicant_count = (
            SELECT COUNT(*)
            FROM applications a
            WHERE a.job_id = jd.id
        )
        WHERE EXISTS (
            SELECT 1 FROM applications a WHERE a.job_id = jd.id
        )
    """)


# ─────────────────────────────────────────────────────────────────────────────
def downgrade() -> None:
    # Intentionally empty:
    # We cannot safely distinguish migrated rows from real applications without
    # storing provenance (e.g., a 'source' column), so we leave the data as-is.
    # To fully roll back Phase 2 you must also run migration 001 downgrade which
    # drops the applications table entirely.
    pass
