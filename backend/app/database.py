"""
database.py
===========
SQLAlchemy async engine with proper table creation ordering.
Fix: init_db imports all models before create_all to ensure
     FK dependencies are resolved correctly.
"""
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

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


# ── ORM Base ──────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


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


# ── Init ──────────────────────────────────────────────────────────────────────
async def init_db() -> None:
    """
    Create pgvector extension and all tables.
    Models must be imported before create_all so SQLAlchemy sees them.
    """
    from sqlalchemy import text

    # Import all models to register them with Base.metadata
    # Order matters: users first (no FKs), then dependent tables
    from app.models.user import User          # noqa: F401
    from app.models.cv import CV              # noqa: F401
    from app.models.job import Job            # noqa: F401
    from app.models.interaction import UserInteraction  # noqa: F401

    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Create all tables defined in ORM models
        await conn.run_sync(Base.metadata.create_all)
