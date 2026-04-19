"""
database.py
===========
SQLAlchemy async engine — Candidate-Only Job Search Platform.

init_db() imports all ORM models before create_all so SQLAlchemy
resolves FK dependencies correctly.

NOTE: Base is imported from app.base (not declared here) so that
Alembic's env.py can import models without needing asyncpg installed locally.
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
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS external_job_id VARCHAR(50)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS company VARCHAR(255)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS company_id VARCHAR(50)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS company_profile TEXT",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS location VARCHAR(255)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS address TEXT",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS link TEXT",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS skills TEXT[]",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS pretty_salary VARCHAR(255)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS salary_currency VARCHAR(20)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS years_of_experience INTEGER",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS job_level VARCHAR(255)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS industry VARCHAR(255)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS job_function VARCHAR(255)",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS job_requirement TEXT",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS benefits TEXT",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS approved_on TIMESTAMPTZ",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS expired_on TIMESTAMPTZ",
        "ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ",
        # Unique index for fast dedup; CREATE IF NOT EXISTS is Postgres 9.5+
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_job_link
        ON job_descriptions (link)
        WHERE link IS NOT NULL
        """,
        # Regular index for company lookups
        "CREATE INDEX IF NOT EXISTS ix_job_descriptions_company ON job_descriptions (company)",
        "CREATE INDEX IF NOT EXISTS ix_job_descriptions_external_job_id ON job_descriptions (external_job_id)",
        "CREATE INDEX IF NOT EXISTS ix_job_descriptions_company_id ON job_descriptions (company_id)",
        # ── User table: Google OAuth columns ──
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT",
        "ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_google_id ON users (google_id) WHERE google_id IS NOT NULL",
    ]

    async with engine.begin() as conn:
        for stmt in _migrations:
            await conn.execute(text(stmt))




# ── Init ──────────────────────────────────────────────────────────────────────
async def init_db() -> None:
    """
    Create pgvector extension and all tables (candidate-only schema).
    Import order respects FK dependencies:
      users → cvs → job_descriptions → interactions
    """
    from sqlalchemy import text

    # ── Import all active models ──────────────────────────────────────────────
    from app.models.user import User                      # noqa: F401
    from app.models.cv import CV                          # noqa: F401  (→ users)
    from app.models.job import Job                        # noqa: F401  (→ users)
    from app.models.interaction import UserInteraction    # noqa: F401  (→ users, cvs, jobs)
    from app.models.model_version import ModelVersion     # noqa: F401
    from app.models.recommendation import Recommendation  # noqa: F401
    from app.models.crawl_log import CrawlLog             # noqa: F401

    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Create all tables defined in ORM models (no-op for existing tables)
        await conn.run_sync(Base.metadata.create_all)

    # Apply idempotent column-level migrations
    await migrate_crawler_columns()
    await migrate_core_indexes()


# ── Core performance indexes (idempotent) ─────────────────────────────────────
async def migrate_core_indexes() -> None:
    """
    CREATE INDEX IF NOT EXISTS for candidate-platform indexes.
    Safe to run on every startup — no-op when indexes already exist.
    """
    from sqlalchemy import text

    _indexes = [
        "CREATE INDEX IF NOT EXISTS ix_job_descriptions_created_at ON job_descriptions (created_at DESC)",
        "CREATE INDEX IF NOT EXISTS ix_job_descriptions_is_active ON job_descriptions (is_active)",
        "CREATE INDEX IF NOT EXISTS ix_interactions_user_id ON user_interactions (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_interactions_job_id ON user_interactions (job_id)",
    ]

    async with engine.begin() as conn:
        for stmt in _indexes:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # index may already exist or table not yet created — non-fatal
