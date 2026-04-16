"""
services/application_service.py
=================================
Business logic for the application flow.

Responsibilities:
  - apply_to_job()           — candidate submits application
  - get_candidate_applications() — candidate lists their own applications
  - get_employer_applications()  — employer sees applicants for their job
  - update_application_status()  — employer moves an application through the pipeline
  - migrate_interactions_to_applications() — one-off data backfill

All database I/O uses the async SQLAlchemy session passed in — no session
creation happens inside this module (pure service functions, easy to test).
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.models.company import Company
from app.models.interaction import UserInteraction
from app.models.job import Job
from app.models.user import User

logger = logging.getLogger(__name__)

# ── Status transition table ───────────────────────────────────────────────────
# Maps current_status → set of valid next statuses.
# Keeping it explicit prevents weird state jumps (e.g. hired → applied).
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "applied":   {"reviewed", "rejected"},
    "reviewed":  {"interview", "rejected"},
    "interview": {"offered", "rejected"},
    "offered":   {"hired", "rejected"},
    "rejected":  set(),          # terminal
    "hired":     set(),          # terminal
}


# ─────────────────────────────────────────────────────────────────────────────
# Candidate operations
# ─────────────────────────────────────────────────────────────────────────────

async def apply_to_job(
    db: AsyncSession,
    *,
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    cv_id: uuid.UUID | None,
    cover_letter: str | None,
) -> Application:
    """
    Submit a job application.

    Raises
    ------
    ValueError("job_not_found")    → caller maps to 404
    ValueError("job_not_published") → caller maps to 400
    ValueError("already_applied")  → caller maps to 409
    """
    # 1. Fetch job
    result = await db.execute(select(Job).where(Job.id == job_id))
    job: Job | None = result.scalar_one_or_none()
    if job is None:
        raise ValueError("job_not_found")

    # 2. Job must be published
    if job.status != "published":
        raise ValueError("job_not_published")

    # 3. Create application — let DB enforce uniqueness
    application = Application(
        job_id=job_id,
        candidate_id=candidate_id,
        cv_id=cv_id,
        cover_letter=cover_letter,
        status=ApplicationStatus.applied,
    )
    db.add(application)

    # 4. Atomically increment applicant_count
    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(applicant_count=Job.applicant_count + 1)
    )

    try:
        await db.flush()   # let UNIQUE constraint fire before commit
    except IntegrityError:
        await db.rollback()
        raise ValueError("already_applied")

    await db.commit()
    await db.refresh(application)
    return application


async def get_candidate_applications(
    db: AsyncSession,
    *,
    candidate_id: uuid.UUID,
) -> list[dict]:
    """
    Return all applications for a candidate, enriched with job + company info.

    Returns a list of plain dicts (avoids lazy-load issues across async boundary).
    """
    # Join application → job → company (LEFT OUTER so jobs without a company still appear)
    stmt = (
        select(Application, Job, Company)
        .join(Job, Application.job_id == Job.id)
        .outerjoin(Company, Job.company_id == Company.id)
        .where(Application.candidate_id == candidate_id)
        .order_by(Application.applied_at.desc())
    )
    rows = (await db.execute(stmt)).all()

    items = []
    for app, job, company in rows:
        items.append({
            "application_id": app.id,
            "job": {
                "id": job.id,
                "title": job.position_title,
                "company_name": company.name if company else job.company,  # fallback to legacy string field
                "status": job.status,
            },
            "status": app.status.value if hasattr(app.status, "value") else app.status,
            "applied_at": app.applied_at,
            "cover_letter": app.cover_letter,
        })
    return items


# ─────────────────────────────────────────────────────────────────────────────
# Employer operations
# ─────────────────────────────────────────────────────────────────────────────

async def get_employer_applications(
    db: AsyncSession,
    *,
    job_id: uuid.UUID,
    employer_id: uuid.UUID,
) -> list[dict]:
    """
    Return all applications for a specific job, verifying employer ownership.

    Raises
    ------
    ValueError("job_not_found")   → 404
    ValueError("forbidden")       → 403  (employer doesn't own the job)
    """
    # 1. Verify job exists
    result = await db.execute(select(Job).where(Job.id == job_id))
    job: Job | None = result.scalar_one_or_none()
    if job is None:
        raise ValueError("job_not_found")

    # 2. Verify ownership via company
    if job.company_id is not None:
        company_result = await db.execute(
            select(Company).where(Company.id == job.company_id)
        )
        company: Company | None = company_result.scalar_one_or_none()
        if company is None or company.owner_id != employer_id:
            raise ValueError("forbidden")
    else:
        # Job not yet linked to a company — only the job creator may view applications
        if job.created_by != employer_id:
            raise ValueError("forbidden")

    # 3. Fetch applications with candidate info
    stmt = (
        select(Application, User)
        .join(User, Application.candidate_id == User.id)
        .where(Application.job_id == job_id)
        .order_by(Application.applied_at.desc())
    )
    rows = (await db.execute(stmt)).all()

    items = []
    for app, candidate in rows:
        items.append({
            "application_id": app.id,
            "candidate": {
                "id": candidate.id,
                "name": candidate.full_name,
                "email": candidate.email,
            },
            "cv_id": app.cv_id,
            "status": app.status.value if hasattr(app.status, "value") else app.status,
            "applied_at": app.applied_at,
            "cover_letter": app.cover_letter,
            "note": app.note,
            "match_score": None,   # Phase 3: filled by ML scoring
        })
    return items


async def update_application_status(
    db: AsyncSession,
    *,
    application_id: uuid.UUID,
    employer_id: uuid.UUID,
    new_status: str,
) -> Application:
    """
    Update the status of an application.

    Validates:
      - Application exists
      - Employer owns the job that this application belongs to
      - Status transition is allowed

    Raises
    ------
    ValueError("application_not_found") → 404
    ValueError("forbidden")             → 403
    ValueError("invalid_transition")    → 400
    """
    # 1. Load application
    result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    app: Application | None = result.scalar_one_or_none()
    if app is None:
        raise ValueError("application_not_found")

    # 2. Verify employer owns the job
    job_result = await db.execute(select(Job).where(Job.id == app.job_id))
    job: Job | None = job_result.scalar_one_or_none()
    if job is None:
        raise ValueError("application_not_found")

    if job.company_id is not None:
        company_result = await db.execute(
            select(Company).where(Company.id == job.company_id)
        )
        company: Company | None = company_result.scalar_one_or_none()
        if company is None or company.owner_id != employer_id:
            raise ValueError("forbidden")
    else:
        if job.created_by != employer_id:
            raise ValueError("forbidden")

    # 3. Validate transition
    current = app.status.value if hasattr(app.status, "value") else str(app.status)
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise ValueError("invalid_transition")

    # 4. Apply update (updated_at handled by DB trigger)
    app.status = ApplicationStatus(new_status)
    await db.commit()
    await db.refresh(app)
    return app


# ─────────────────────────────────────────────────────────────────────────────
# Data migration: user_interactions → applications
# ─────────────────────────────────────────────────────────────────────────────

async def migrate_interactions_to_applications(db: AsyncSession) -> dict:
    """
    One-off migration: copy user_interactions(action='applied') rows into the
    applications table, ignoring duplicates.

    Returns a summary dict: {'migrated': N, 'skipped': N, 'errors': N}
    """
    stmt = select(UserInteraction).where(
        UserInteraction.action == "applied"  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    interactions = result.scalars().all()

    migrated = skipped = errors = 0

    for interaction in interactions:
        # Check if already migrated (duplicate guard)
        existing = await db.execute(
            select(Application).where(
                Application.job_id == interaction.job_id,
                Application.candidate_id == interaction.user_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            skipped += 1
            continue

        try:
            app = Application(
                job_id=interaction.job_id,
                candidate_id=interaction.user_id,
                cv_id=interaction.cv_id,
                status=ApplicationStatus.applied,
                applied_at=interaction.created_at,
            )
            db.add(app)
            await db.flush()
            migrated += 1
        except IntegrityError:
            await db.rollback()
            skipped += 1
        except Exception as exc:
            logger.error(f"[migrate] Failed for interaction {interaction.id}: {exc}")
            await db.rollback()
            errors += 1

    await db.commit()
    logger.info(f"[migrate] Done — migrated={migrated} skipped={skipped} errors={errors}")
    return {"migrated": migrated, "skipped": skipped, "errors": errors}
