"""
services/job_service.py
========================
Public job listing service for candidates.

All jobs in the DB are crawled from VietnamWorks and are public — no
employer ownership, no status filtering (all active is_active=True).

Responsibilities:
  - list_jobs()   — paginated, filterable job listing
  - get_job()     — single job detail by ID
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job

logger = logging.getLogger(__name__)


async def list_jobs(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    location: str | None = None,
    job_type: str | None = None,
    company: str | None = None,
) -> dict:
    """
    Return a paginated list of active public jobs.

    Filters
    -------
    search   : keyword match against position_title OR description
    location : partial match on location field
    job_type : exact match (full-time, part-time, remote, etc.)
    company  : partial match on company name

    Returns
    -------
    dict with keys: items, total, page, page_size
    """
    base = select(Job).where(Job.is_active.is_(True))
    count_base = select(func.count(Job.id)).where(Job.is_active.is_(True))

    if search:
        pattern = f"%{search}%"
        keyword_filter = or_(
            Job.position_title.ilike(pattern),
            Job.description.ilike(pattern),
        )
        base = base.where(keyword_filter)
        count_base = count_base.where(keyword_filter)

    if location:
        loc_filter = Job.location.ilike(f"%{location}%")
        base = base.where(loc_filter)
        count_base = count_base.where(loc_filter)

    if job_type:
        base = base.where(Job.job_type == job_type)
        count_base = count_base.where(Job.job_type == job_type)

    if company:
        co_filter = Job.company.ilike(f"%{company}%")
        base = base.where(co_filter)
        count_base = count_base.where(co_filter)

    total = (await db.execute(count_base)).scalar_one()

    jobs = (
        await db.execute(
            base
            .order_by(Job.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return {
        "items": list(jobs),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_job(
    db: AsyncSession,
    *,
    job_id: uuid.UUID,
) -> Job | None:
    """
    Return a single active job by ID, or None if not found / inactive.
    """
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.is_active.is_(True))
    )
    return result.scalar_one_or_none()
