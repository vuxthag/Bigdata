"""
Phase 6 – Full-Text Search for Job Discovery.

Revision: 006_fulltext_search
Parent:   005_cleanup

Changes
-------
Adds a PostgreSQL GIN full-text search index on job_descriptions for fast
keyword search — the same technique used by real job platforms (VietnamWorks,
LinkedIn, Indeed).

1. Adds a generated tsvector column `search_vector` combining:
   - position_title (weight A — highest)
   - company        (weight B)
   - skills array   (weight B)
   - description    (weight C)

2. Creates a GIN index on the column for sub-millisecond lookups.

3. Creates a trigger to keep the vector updated on INSERT/UPDATE.
"""
from __future__ import annotations

from alembic import op

revision: str = "006_fulltext_search"
down_revision: str | None = "005_candidate_platform"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # 1. Add tsvector column
    op.execute("""
        ALTER TABLE job_descriptions
        ADD COLUMN IF NOT EXISTS search_vector tsvector
    """)

    # 2. Populate it for all existing rows
    op.execute("""
        UPDATE job_descriptions SET search_vector =
            setweight(to_tsvector('english', COALESCE(position_title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(company, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(array_to_string(skills, ' '), '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(industry, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(job_function, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(LEFT(description, 2000), '')), 'D')
    """)

    # 3. GIN index for fast full-text search
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_job_search_vector
        ON job_descriptions USING GIN (search_vector)
    """)

    # 4. Trigger function to auto-update on INSERT/UPDATE
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_job_search_vector_update()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.position_title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.company, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(array_to_string(NEW.skills, ' '), '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.industry, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.job_function, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(LEFT(NEW.description, 2000), '')), 'D');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_job_search_vector ON job_descriptions;
        CREATE TRIGGER trg_job_search_vector
        BEFORE INSERT OR UPDATE OF position_title, company, skills, industry, job_function, description
        ON job_descriptions
        FOR EACH ROW
        EXECUTE FUNCTION fn_job_search_vector_update();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_job_search_vector ON job_descriptions")
    op.execute("DROP FUNCTION IF EXISTS fn_job_search_vector_update()")
    op.execute("DROP INDEX IF EXISTS ix_job_search_vector")
    op.execute("ALTER TABLE job_descriptions DROP COLUMN IF EXISTS search_vector")
