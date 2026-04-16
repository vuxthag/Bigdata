"""
services/job_service.py
========================
Business logic for employer job management (Phase 3).

Responsibilities:
  - create_job()           — create draft job linked to employer's company
  - get_employer_jobs()    — paginated list with optional status filter
  - get_job_detail()       — single job with ownership check
  - update_job()           — update editable fields (draft or published only)
  - publish_job()          — draft → published
  - close_job()            — published → closed
  - delete_job()           — hard-delete draft jobs only

All DB I/O uses the async SQLAlchemy session passed in.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import Company
from app.models.job import Job

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _assert_owns_job(
    db: AsyncSession,
    *,
    job_id: uuid.UUID,
    employer_id: uuid.UUID,
) -> Job:
    """
    Load the job and verify it belongs to the calling employer.

    Raises
    ------
    ValueError("job_not_found")  → 404
    ValueError("forbidden")      → 403
    """
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.company_rel))
        .where(Job.id == job_id)
    )
    job: Job | None = result.scalar_one_or_none()
    if job is None:
        raise ValueError("job_not_found")

    # Ownership check: prefer company link, fall back to created_by
    if job.company_id is not None:
        if job.company_rel is None or job.company_rel.owner_id != employer_id:
            raise ValueError("forbidden")
    else:
        if job.created_by != employer_id:
            raise ValueError("forbidden")

    return job


# ─────────────────────────────────────────────────────────────────────────────
# CRUD + lifecycle
# ─────────────────────────────────────────────────────────────────────────────

async def create_job(
    db: AsyncSession,
    *,
    employer_id: uuid.UUID,
    position_title: str,
    description: str,
    location: str | None = None,
    job_type: str | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    deadline: date | None = None,
    skills: list[str] | None = None,
) -> Job:
    """
    Create a new job as a draft, linked to the employer's company.

    Raises
    ------
    ValueError("no_company")  → employer has no company yet  → 400
    """
    # Require company before posting jobs
    company_result = await db.execute(
        select(Company).where(Company.owner_id == employer_id)
    )
    company: Company | None = company_result.scalar_one_or_none()
    if company is None:
        raise ValueError("no_company")

    job = Job(
        position_title=position_title,
        description=description,
        company_id=company.id,
        created_by=employer_id,
        status="draft",
        location=location,
        job_type=job_type,
        salary_min=salary_min,
        salary_max=salary_max,
        deadline=deadline,
        skills=skills,
        source="employer",
        is_active=True,
    )
    db.add(job)
    await db.flush()
    await db.commit()
    await db.refresh(job)
    logger.info(f"[job] Draft job {job.id} created by employer {employer_id}")
    return job


async def get_employer_jobs(
    db: AsyncSession,
    *,
    employer_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
) -> dict:
    """
    Return paginated list of jobs owned by the employer.

    Returns
    -------
    dict with keys: items, total, page, page_size, status_filter
    """
    # Resolve company for this employer
    company_result = await db.execute(
        select(Company).where(Company.owner_id == employer_id)
    )
    company: Company | None = company_result.scalar_one_or_none()

    # Base query — jobs linked either by company_id or created_by
    if company is not None:
        base_filter = Job.company_id == company.id
    else:
        base_filter = Job.created_by == employer_id

    query = select(Job).options(selectinload(Job.company_rel)).where(base_filter)
    count_query = select(func.count(Job.id)).where(base_filter)

    if status_filter:
        query = query.where(Job.status == status_filter)
        count_query = count_query.where(Job.status == status_filter)

    total = (await db.execute(count_query)).scalar_one()

    query = (
        query
        .order_by(Job.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    jobs = (await db.execute(query)).scalars().all()

    return {
        "items": list(jobs),
        "total": total,
        "page": page,
        "page_size": page_size,
        "status_filter": status_filter,
    }


async def get_job_detail(
    db: AsyncSession,
    *,
    job_id: uuid.UUID,
    employer_id: uuid.UUID,
) -> Job:
    """
    Return full job detail, enforcing ownership.

    Raises
    ------
    ValueError("job_not_found") → 404
    ValueError("forbidden")     → 403
    """
    return await _assert_owns_job(db, job_id=job_id, employer_id=employer_id)


async def update_job(
    db: AsyncSession,
    *,
    job_id: uuid.UUID,
    employer_id: uuid.UUID,
    position_title: str | None = None,
    description: str | None = None,
    location: str | None = None,
    job_type: str | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    deadline: date | None = None,
    skills: list[str] | None = None,
) -> Job:
    """
    Update mutable fields of a job.

    Rules:
      - Only editable when status is 'draft' or 'published'
      - Cannot edit 'closed' jobs

    Raises
    ------
    ValueError("job_not_found")   → 404
    ValueError("forbidden")       → 403
    ValueError("job_closed")      → 400
    """
    job = await _assert_owns_job(db, job_id=job_id, employer_id=employer_id)

    if job.status == "closed":
        raise ValueError("job_closed")

    if position_title is not None:
        job.position_title = position_title
    if description is not None:
        job.description = description
    if location is not None:
        job.location = location
    if job_type is not None:
        job.job_type = job_type
    if salary_min is not None:
        job.salary_min = salary_min
    if salary_max is not None:
        job.salary_max = salary_max
    if deadline is not None:
        job.deadline = deadline
    if skills is not None:
        job.skills = skills

    await db.commit()
    await db.refresh(job)
    return job


async def publish_job(
    db: AsyncSession,
    *,
    job_id: uuid.UUID,
    employer_id: uuid.UUID,
) -> Job:
    """
    Publish a draft job (draft → published).

    Validates required fields are present before transitioning.

    Raises
    ------
    ValueError("job_not_found")      → 404
    ValueError("forbidden")          → 403
    ValueError("already_published")  → 400
    ValueError("job_closed")         → 400
    ValueError("missing_fields")     → 400  (title or description empty)
    """
    job = await _assert_owns_job(db, job_id=job_id, employer_id=employer_id)

    if job.status == "published":
        raise ValueError("already_published")
    if job.status == "closed":
        raise ValueError("job_closed")

    # Validate required fields
    if not job.position_title or not job.description:
        raise ValueError("missing_fields")

    job.status = "published"
    await db.commit()
    await db.refresh(job)
    logger.info(f"[job] Job {job_id} published by employer {employer_id}")
    return job


async def close_job(
    db: AsyncSession,
    *,
    job_id: uuid.UUID,
    employer_id: uuid.UUID,
) -> Job:
    """
    Close a job (published → closed).

    Draft jobs can also be closed directly.

    Raises
    ------
    ValueError("job_not_found")  → 404
    ValueError("forbidden")      → 403
    ValueError("already_closed") → 400
    """
    job = await _assert_owns_job(db, job_id=job_id, employer_id=employer_id)

    if job.status == "closed":
        raise ValueError("already_closed")

    job.status = "closed"
    await db.commit()
    await db.refresh(job)
    logger.info(f"[job] Job {job_id} closed by employer {employer_id}")
    return job


async def delete_job(
    db: AsyncSession,
    *,
    job_id: uuid.UUID,
    employer_id: uuid.UUID,
) -> None:
    """
    Hard-delete a draft job.

    Rules:
      - Only 'draft' jobs may be deleted
      - Published or closed jobs are protected

    Raises
    ------
    ValueError("job_not_found")      → 404
    ValueError("forbidden")          → 403
    ValueError("cannot_delete")      → 400  (not a draft)
    """
    job = await _assert_owns_job(db, job_id=job_id, employer_id=employer_id)

    if job.status != "draft":
        raise ValueError("cannot_delete")

    await db.delete(job)
    await db.commit()
    logger.info(f"[job] Draft job {job_id} deleted by employer {employer_id}")
