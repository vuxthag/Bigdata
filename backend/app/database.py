"""
database.py
===========
SQLAlchemy async engine with proper table creation ordering.
Fix: init_db imports all models before create_all to ensure
     FK dependencies are resolved correctly.

Added: migrate_crawler_columns()  — safe ALTER TABLE for crawler fields.
Added: migrate_phase1_columns()   — safe ALTER TABLE for Phase 1 fields
       (role on users, company_id/status/salary/etc. on job_descriptions).

NOTE: Base is imported from app.base (not declared here) so that Alembic's
env.py can import models without needing asyncpg installed locally.
"""
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Re-export Base so that existing `from app.database import Base` still works.
from app.base import Base  # noqa: F401

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── FastAPI dependency ────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session, closing it after the request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Crawler column migration (idempotent) ─────────────────────────────────────
async def migrate_crawler_columns() -> None:
    """
    Add crawler-specific columns to job_descriptions if they don't exist yet.
    Uses ADD COLUMN IF NOT EXISTS so it's safe to run on every startup.
    Also creates a unique index on the link column for O(1) dedup lookups.
    """
    from sqlalchemy import text

    _migrations = [
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS company VARCHAR(255)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS location VARCHAR(255)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS link TEXT",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS skills TEXT[]",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ",
        # Unique index for fast dedup; CREATE IF NOT EXISTS is Postgres 9.5+
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_job_link
        ON job_descriptions (link)
        WHERE link IS NOT NULL
        """,
        # Regular index for company lookups
        "CREATE INDEX IF NOT EXISTS ix_job_descriptions_company ON job_descriptions (company)",
    ]

    async with engine.begin() as conn:
        for stmt in _migrations:
            await conn.execute(text(stmt))


# ── Phase 1 column migrations (idempotent) ────────────────────────────────────
async def migrate_phase1_columns() -> None:
    """
    Idempotent ALTER TABLE statements for all Phase 1 schema additions.
    Safe to run on every startup — ADD COLUMN IF NOT EXISTS is a no-op when
    the column already exists (Postgres 9.6+).

    Covers:
      1. users.role          — RBAC column
      2. job_descriptions.*  — company_id, status, salary, job_type, deadline,
                               applicant_count
    Note: companies and applications tables are created via create_all()
    from the ORM models (they are brand-new tables, not ALTER operations).
    """
    from sqlalchemy import text

    _migrations = [
        # ── users: RBAC role ──────────────────────────────────────────────────
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'candidate'",
        # CHECK constraint (idempotent via DO block)
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ck_users_role'
                  AND conrelid = 'users'::regclass
            ) THEN
                ALTER TABLE users
                    ADD CONSTRAINT ck_users_role
                    CHECK (role IN ('candidate', 'employer', 'admin'));
            END IF;
        END $$;
        """,

        # ── job_descriptions: Phase 1 fields ──────────────────────────────────
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES companies(id) ON DELETE SET NULL",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'published'",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS salary_min INT",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS salary_max INT",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS job_type VARCHAR(50)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS deadline DATE",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS applicant_count INT NOT NULL DEFAULT 0",
        # CHECK constraint for status
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ck_job_status'
                  AND conrelid = 'job_descriptions'::regclass
            ) THEN
                ALTER TABLE job_descriptions
                    ADD CONSTRAINT ck_job_status
                    CHECK (status IN ('draft', 'published', 'closed'));
            END IF;
        END $$;
        """,
        # Index for company_id lookups
        "CREATE INDEX IF NOT EXISTS ix_job_descriptions_company_id ON job_descriptions (company_id)",
    ]

    async with engine.begin() as conn:
        for stmt in _migrations:
            await conn.execute(text(stmt))


# ── Init ──────────────────────────────────────────────────────────────────────
async def init_db() -> None:
    """
    Create pgvector extension and all tables.
    Models must be imported before create_all so SQLAlchemy sees them.
    Import order respects FK dependencies:
      users → cvs / companies → job_descriptions → interactions / applications
    """
    from sqlalchemy import text

    # ── Import all models (registration order matters for FK resolution) ──────
    from app.models.user import User                      # noqa: F401  (no FK deps)
    from app.models.cv import CV                          # noqa: F401  (→ users)
    from app.models.company import Company                # noqa: F401  (→ users)  [Phase 1]
    from app.models.job import Job                        # noqa: F401  (→ users, companies)
    from app.models.interaction import UserInteraction    # noqa: F401  (→ users, cvs, jobs)
    from app.models.application import Application        # noqa: F401  (→ jobs, users, cvs) [Phase 1]
    from app.models.model_version import ModelVersion     # noqa: F401
    from app.models.recommendation import Recommendation  # noqa: F401
    from app.models.analytics_log import AnalyticsLog    # noqa: F401
    from app.models.crawl_log import CrawlLog             # noqa: F401

    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Create all tables defined in ORM models (no-op for existing tables)
        await conn.run_sync(Base.metadata.create_all)

    # Apply idempotent column-level migrations
    await migrate_crawler_columns()
    await migrate_phase1_columns()
    await migrate_phase3_indexes()


# ── Phase 3 performance indexes (idempotent) ──────────────────────────────────
async def migrate_phase3_indexes() -> None:
    """
    CREATE INDEX IF NOT EXISTS for all Phase 3 performance indexes.
    Safe to run on every startup — no-op when indexes already exist.
    """
    from sqlalchemy import text

    _indexes = [
        "CREATE INDEX IF NOT EXISTS ix_job_descriptions_status ON job_descriptions (status)",
        "CREATE INDEX IF NOT EXISTS ix_job_descriptions_created_at ON job_descriptions (created_at DESC)",
        "CREATE INDEX IF NOT EXISTS ix_job_descriptions_company_status ON job_descriptions (company_id, status)",
        "CREATE INDEX IF NOT EXISTS ix_applications_status ON applications (status)",
        "CREATE INDEX IF NOT EXISTS ix_users_role ON users (role)",
    ]

    async with engine.begin() as conn:
        for stmt in _indexes:
            await conn.execute(text(stmt))
