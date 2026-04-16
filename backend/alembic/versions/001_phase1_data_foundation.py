"""
Phase 1 – Data Foundation migration.

Revision: 001_phase1_data_foundation
Generated: 2026-04-16

Changes
-------
1. users          – ADD COLUMN role VARCHAR(20) + CHECK constraint
2. companies      – CREATE TABLE (owner → users)
3. job_descriptions – ADD COLUMNS company_id, status, salary_min, salary_max,
                      job_type, deadline, applicant_count + CHECK constraint
4. applications   – CREATE TABLE (job → job_descriptions, candidate → users,
                    cv → cvs, UNIQUE job+candidate)

Down
----
Reverses all of the above in dependency order (applications → job cols →
companies → user role).

Notes
-----
* `alembic_version` tracking lets you re-run upgrade/downgrade safely.
* All new job_descriptions columns are nullable (backward compat) except
  status and applicant_count which have server defaults.
* The `application_status_enum` Postgres type is created/dropped here.
* `gen_random_uuid()` requires pgcrypto; we CREATE EXTENSION IF NOT EXISTS.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "001_phase1"
down_revision: str | None = None      # first migration — no parent
branch_labels: str | None = None
depends_on: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
def upgrade() -> None:
    # 0. Extensions -----------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ─────────────────────────────────────────────────────────────────────────
    # 1. users — add role column + CHECK constraint
    # ─────────────────────────────────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
            server_default="candidate",
        ),
    )
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('candidate', 'employer', 'admin')",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. companies — new table
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "companies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=True),
        sa.Column("logo_url", sa.Text, nullable=True),
        sa.Column("website", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("size", sa.String(50), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Constraints
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"],
            name="fk_company_owner",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("owner_id", name="uq_company_owner"),
        sa.UniqueConstraint("slug",     name="uq_company_slug"),
    )
    op.create_index("ix_companies_owner_id", "companies", ["owner_id"])

    # ─────────────────────────────────────────────────────────────────────────
    # 3. job_descriptions — add Phase 1 columns
    # ─────────────────────────────────────────────────────────────────────────
    op.add_column(
        "job_descriptions",
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="SET NULL", name="fk_job_company"),
            nullable=True,
        ),
    )
    op.add_column(
        "job_descriptions",
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="published",
        ),
    )
    op.add_column("job_descriptions", sa.Column("salary_min", sa.Integer, nullable=True))
    op.add_column("job_descriptions", sa.Column("salary_max", sa.Integer, nullable=True))
    op.add_column("job_descriptions", sa.Column("job_type",   sa.String(50), nullable=True))
    op.add_column("job_descriptions", sa.Column("deadline",   sa.Date, nullable=True))
    op.add_column(
        "job_descriptions",
        sa.Column("applicant_count", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_check_constraint(
        "ck_job_status",
        "job_descriptions",
        "status IN ('draft', 'published', 'closed')",
    )
    op.create_index(
        "ix_job_descriptions_company_id", "job_descriptions", ["company_id"]
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 4. applications — new table (replaces user_interactions(action='applied'))
    # ─────────────────────────────────────────────────────────────────────────
    # Drop orphaned ENUM type if it exists from a previous failed run
    op.execute("DROP TYPE IF EXISTS application_status_enum CASCADE")

    op.create_table(
        "applications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("job_id",       postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cv_id",        postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "applied", "reviewed", "interview", "offered", "rejected", "hired",
                name="application_status_enum",
            ),
            nullable=False,
            server_default="applied",
        ),
        sa.Column("cover_letter", sa.Text, nullable=True),
        sa.Column("note",         sa.Text, nullable=True),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Foreign Keys
        sa.ForeignKeyConstraint(
            ["job_id"], ["job_descriptions.id"],
            name="fk_application_job",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["users.id"],
            name="fk_application_candidate",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["cv_id"], ["cvs.id"],
            name="fk_application_cv",
            ondelete="SET NULL",
        ),
        # Business rule: one application per (job, candidate)
        sa.UniqueConstraint("job_id", "candidate_id", name="unique_application"),
    )
    op.create_index("ix_applications_job_id",       "applications", ["job_id"])
    op.create_index("ix_applications_candidate_id", "applications", ["candidate_id"])

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Auto-update trigger for applications.updated_at
    # ─────────────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_applications_updated_at
        BEFORE UPDATE ON applications
        FOR EACH ROW
        EXECUTE FUNCTION fn_set_updated_at();
    """)

    op.execute("""
        CREATE TRIGGER trg_companies_updated_at
        BEFORE UPDATE ON companies
        FOR EACH ROW
        EXECUTE FUNCTION fn_set_updated_at();
    """)


# ─────────────────────────────────────────────────────────────────────────────
def downgrade() -> None:
    # Reverse in dependency order (applications first, then jobs, companies, users)

    # 5. Drop triggers & function
    op.execute("DROP TRIGGER IF EXISTS trg_applications_updated_at ON applications")
    op.execute("DROP TRIGGER IF EXISTS trg_companies_updated_at    ON companies")
    op.execute("DROP FUNCTION IF EXISTS fn_set_updated_at()")

    # 4. applications table
    op.drop_index("ix_applications_candidate_id", table_name="applications")
    op.drop_index("ix_applications_job_id",        table_name="applications")
    op.drop_table("applications")
    op.execute("DROP TYPE IF EXISTS application_status_enum")

    # 3. job_descriptions Phase 1 columns
    op.drop_index("ix_job_descriptions_company_id", table_name="job_descriptions")
    op.drop_constraint("ck_job_status",  "job_descriptions", type_="check")
    op.drop_column("job_descriptions", "applicant_count")
    op.drop_column("job_descriptions", "deadline")
    op.drop_column("job_descriptions", "job_type")
    op.drop_column("job_descriptions", "salary_max")
    op.drop_column("job_descriptions", "salary_min")
    op.drop_column("job_descriptions", "status")
    op.drop_column("job_descriptions", "company_id")

    # 2. companies table
    op.drop_index("ix_companies_owner_id", table_name="companies")
    op.drop_table("companies")

    # 1. users role column
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
