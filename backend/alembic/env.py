"""
alembic/env.py
==============
Alembic migration environment.

Design decisions:
  - Reads DATABASE_URL from .env via pydantic-settings (same as the app).
  - Alembic requires a *synchronous* database URL; we swap the asyncpg
    driver for psycopg2 automatically.
  - target_metadata is set to Base.metadata so `alembic revision --autogenerate`
    can diff the ORM models against the live schema.
  - All ORM models are imported before run_migrations_online() to ensure
    Base.metadata is fully populated.
"""
from __future__ import annotations

import re
import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Add backend root to sys.path so `app.*` imports resolve ──────────────────
# alembic/ lives inside backend/, so we go up one level.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Load application settings (reads .env) ───────────────────────────────────
from app.config import settings  # noqa: E402

# ── Import ORM Base (from app.base — avoids async engine creation) ────────────
from app.base import Base  # noqa: E402

# ── Import every model so Base.metadata is fully populated ───────────────────
# Order: no-FK tables first, then tables that reference them.
from app.models.user import User                      # noqa: F401
from app.models.cv import CV                          # noqa: F401
from app.models.company import Company                # noqa: F401
from app.models.job import Job                        # noqa: F401
from app.models.interaction import UserInteraction    # noqa: F401
from app.models.application import Application        # noqa: F401
from app.models.model_version import ModelVersion     # noqa: F401
from app.models.recommendation import Recommendation  # noqa: F401
from app.models.analytics_log import AnalyticsLog    # noqa: F401
from app.models.crawl_log import CrawlLog             # noqa: F401

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic which metadata to diff against
target_metadata = Base.metadata


# ── Convert async URL → sync URL ─────────────────────────────────────────────
def _make_sync_url(async_url: str) -> str:
    """
    Alembic uses a synchronous connection; we swap the driver:
      postgresql+asyncpg://... → postgresql+psycopg2://...
    If the URL already uses psycopg2 (or bare postgresql://), leave it.
    """
    return re.sub(r"postgresql\+asyncpg://", "postgresql+psycopg2://", async_url)


SYNC_DB_URL = _make_sync_url(settings.DATABASE_URL)


# ── Migration helpers ─────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Run migrations without a live DB connection (generates SQL to stdout).
    Useful for reviewing DDL before applying.
    """
    context.configure(
        url=SYNC_DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = SYNC_DB_URL

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
