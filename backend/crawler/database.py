"""
crawler/database.py
===================
Async DB helpers scoped to the crawler subsystem.

Responsibilities:
  - upsert_job(): insert new job or update existing (by unique link)
  - get_crawled_links(): fast in-memory dedup set

Uses the existing SQLAlchemy async engine from app.database.
After each new job insert, triggers real-time recommendation matching.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Set, Tuple

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job

logger = logging.getLogger(__name__)


async def get_crawled_links(session: AsyncSession) -> Set[str]:
    """
    Return the set of all job links already stored in the DB.
    Used to build an in-memory dedup cache before processing a batch.
    """
    result = await session.execute(
        select(Job.link).where(Job.link.isnot(None))
    )
    links = {row[0] for row in result.fetchall()}
    logger.debug(f"[CrawlerDB] Loaded {len(links)} existing links for dedup")
    return links


async def upsert_job(
    session: AsyncSession,
    job_data: dict,
) -> Tuple[bool, bool]:
    """
    Insert a new job or update an existing one identified by `link`.

    Args:
        session:   SQLAlchemy async session
        job_data:  dict with keys matching Job model fields

    Returns:
        (inserted, updated) — exactly one will be True, or both False on error.
    """
    link = job_data.get("link")
    if not link:
        logger.warning("[CrawlerDB] upsert_job called with no link — skipping")
        return False, False

    try:
        # Check existence
        result = await session.execute(
            select(Job.id, Job.cleaned_description).where(Job.link == link)
        )
        existing = result.first()

        now = datetime.now(timezone.utc)

        if existing is None:
            # ── INSERT ─────────────────────────────────────────────────────
            job = Job(
                position_title=job_data.get("position_title", "Unknown"),
                description=job_data.get("description", ""),
                cleaned_description=job_data.get("cleaned_description"),
                embedding=job_data.get("embedding"),
                source=job_data.get("source", "unknown"),
                company=job_data.get("company"),
                location=job_data.get("location"),
                link=link,
                skills=job_data.get("skills", []),
                created_at=now,
                updated_at=now,
                is_active=True,
            )
            session.add(job)
            await session.flush()  # flush so job.id is populated
            logger.debug(f"[CrawlerDB] Inserted: {link}")

            # ── Trigger real-time recommendations for new job ───────────────
            if job_data.get("embedding") is not None:
                try:
                    from app.services.recommendation_trigger import trigger_recommendations_for_new_job
                    await trigger_recommendations_for_new_job(job.id, session)
                except Exception as trigger_exc:
                    # Non-critical: log and continue — don't fail the whole insert
                    logger.warning(f"[CrawlerDB] Recommendation trigger failed for {link}: {trigger_exc}")

            return True, False

        else:
            job_id, old_desc = existing

            # ── UPDATE if content changed ───────────────────────────────────
            new_desc = job_data.get("cleaned_description") or job_data.get("description", "")
            if old_desc != new_desc:
                await session.execute(
                    update(Job)
                    .where(Job.id == job_id)
                    .values(
                        description=job_data.get("description", ""),
                        cleaned_description=job_data.get("cleaned_description"),
                        embedding=job_data.get("embedding"),
                        company=job_data.get("company"),
                        location=job_data.get("location"),
                        skills=job_data.get("skills", []),
                        updated_at=now,
                    )
                )
                logger.debug(f"[CrawlerDB] Updated: {link}")
                return False, True

            logger.debug(f"[CrawlerDB] Unchanged (skip): {link}")
            return False, False

    except Exception as exc:
        logger.error(f"[CrawlerDB] upsert_job error for {link}: {exc}")
        raise
