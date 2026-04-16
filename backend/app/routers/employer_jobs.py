"""
routers/employer_jobs.py
=========================
Employer job management endpoints (Phase 3).

Routes
------
POST   /api/v1/employer/jobs                          — create job (draft)
GET    /api/v1/employer/jobs                          — list my jobs (paginated)
GET    /api/v1/employer/jobs/{job_id}                 — get single job
PUT    /api/v1/employer/jobs/{job_id}                 — update job
PATCH  /api/v1/employer/jobs/{job_id}/publish         — publish (draft → published)
PATCH  /api/v1/employer/jobs/{job_id}/close           — close  (published → closed)
DELETE /api/v1/employer/jobs/{job_id}                 — delete draft job

Auth: JWT required, role must be 'employer'.
Ownership: every mutation verifies job.company.owner_id == current_user.id.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.job_schema import (
    EmployerCompanyBrief,
    EmployerJobCreate,
    EmployerJobCreateResponse,
    EmployerJobListResponse,
    EmployerJobResponse,
    EmployerJobUpdate,
    JobStatusUpdateResponse,
)
from app.services.auth_service import get_current_user
from app.services.job_service import (
    close_job,
    create_job,
    delete_job,
    get_employer_jobs,
    get_job_detail,
    publish_job,
    update_job,
)

router = APIRouter(prefix="/employer/jobs", tags=["Employer — Jobs"])


# ── Guards ────────────────────────────────────────────────────────────────────

def _require_employer(current_user: User) -> User:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can access this endpoint",
        )
    return current_user


# ── Error mapping ─────────────────────────────────────────────────────────────

def _map_job_error(exc: ValueError) -> None:
    code = str(exc)
    mapping = {
        "job_not_found":      (status.HTTP_404_NOT_FOUND,  "Job not found"),
        "forbidden":          (status.HTTP_403_FORBIDDEN,   "You do not own this job"),
        "no_company":         (status.HTTP_400_BAD_REQUEST,
                               "Create a company profile first (POST /employer/company)"),
        "job_closed":         (status.HTTP_400_BAD_REQUEST, "Cannot edit a closed job"),
        "already_published":  (status.HTTP_400_BAD_REQUEST, "Job is already published"),
        "already_closed":     (status.HTTP_400_BAD_REQUEST, "Job is already closed"),
        "missing_fields":     (status.HTTP_400_BAD_REQUEST,
                               "Cannot publish: job must have a title and description"),
        "cannot_delete":      (status.HTTP_400_BAD_REQUEST,
                               "Only draft jobs can be deleted. Close the job first if needed."),
    }
    http_status, detail = mapping.get(code, (status.HTTP_500_INTERNAL_SERVER_ERROR, code))
    raise HTTPException(status_code=http_status, detail=detail)


# ── Serialization helper ──────────────────────────────────────────────────────

def _serialize_job(job) -> EmployerJobResponse:
    company_brief = None
    if job.company_rel is not None:
        company_brief = EmployerCompanyBrief(
            id=job.company_rel.id,
            name=job.company_rel.name,
            slug=job.company_rel.slug,
        )
    return EmployerJobResponse(
        id=job.id,
        position_title=job.position_title,
        description=job.description,
        location=job.location,
        job_type=job.job_type,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        deadline=job.deadline,
        skills=job.skills,
        status=job.status,
        applicant_count=job.applicant_count,
        company=company_brief,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


# ── POST /employer/jobs ───────────────────────────────────────────────────────

@router.post(
    "",
    response_model=EmployerJobCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new job (draft)",
)
async def create_employer_job(
    body: EmployerJobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployerJobCreateResponse:
    """
    Create a new job posting in **draft** status.

    - Requires the employer to have an existing company profile.
    - The job is **not visible** to candidates until published.
    """
    _require_employer(current_user)

    try:
        job = await create_job(
            db,
            employer_id=current_user.id,
            position_title=body.position_title,
            description=body.description,
            location=body.location,
            job_type=body.job_type,
            salary_min=body.salary_min,
            salary_max=body.salary_max,
            deadline=body.deadline,
            skills=body.skills,
        )
    except ValueError as exc:
        _map_job_error(exc)

    return EmployerJobCreateResponse(job_id=job.id, status=job.status)


# ── GET /employer/jobs ────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=EmployerJobListResponse,
    summary="List my jobs",
)
async def list_employer_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Filter by status: draft | published | closed",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployerJobListResponse:
    """
    Return a paginated list of jobs owned by the authenticated employer.

    Optional query params:
    - `status`: filter by `draft`, `published`, or `closed`
    - `page` / `page_size`: pagination controls
    """
    _require_employer(current_user)

    # Validate status filter value
    if status_filter and status_filter not in ("draft", "published", "closed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status filter. Use: draft | published | closed",
        )

    result = await get_employer_jobs(
        db,
        employer_id=current_user.id,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
    )

    return EmployerJobListResponse(
        items=[_serialize_job(j) for j in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        status_filter=result["status_filter"],
    )


# ── GET /employer/jobs/{job_id} ───────────────────────────────────────────────

@router.get(
    "/{job_id}",
    response_model=EmployerJobResponse,
    summary="Get job detail",
)
async def get_employer_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployerJobResponse:
    """
    Return full detail for a single job the employer owns.
    Returns **403** if the job belongs to another employer.
    """
    _require_employer(current_user)

    try:
        job = await get_job_detail(db, job_id=job_id, employer_id=current_user.id)
    except ValueError as exc:
        _map_job_error(exc)

    return _serialize_job(job)


# ── PUT /employer/jobs/{job_id} ───────────────────────────────────────────────

@router.put(
    "/{job_id}",
    response_model=EmployerJobResponse,
    summary="Update a job",
)
async def update_employer_job(
    job_id: uuid.UUID,
    body: EmployerJobUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployerJobResponse:
    """
    Update job fields. Works on **draft** and **published** jobs.
    Returns **400** if the job is already closed.
    """
    _require_employer(current_user)

    try:
        job = await update_job(
            db,
            job_id=job_id,
            employer_id=current_user.id,
            position_title=body.position_title,
            description=body.description,
            location=body.location,
            job_type=body.job_type,
            salary_min=body.salary_min,
            salary_max=body.salary_max,
            deadline=body.deadline,
            skills=body.skills,
        )
    except ValueError as exc:
        _map_job_error(exc)

    return _serialize_job(job)


# ── PATCH /employer/jobs/{job_id}/publish ─────────────────────────────────────

@router.patch(
    "/{job_id}/publish",
    response_model=JobStatusUpdateResponse,
    summary="Publish a draft job",
)
async def publish_employer_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobStatusUpdateResponse:
    """
    Transition a job from **draft → published**.

    Once published, the job is visible to candidates and can accept applications.
    Requires `position_title` and `description` to be non-empty.
    """
    _require_employer(current_user)

    try:
        job = await publish_job(db, job_id=job_id, employer_id=current_user.id)
    except ValueError as exc:
        _map_job_error(exc)

    return JobStatusUpdateResponse(
        job_id=job.id,
        status=job.status,
        message="Job published successfully",
    )


# ── PATCH /employer/jobs/{job_id}/close ───────────────────────────────────────

@router.patch(
    "/{job_id}/close",
    response_model=JobStatusUpdateResponse,
    summary="Close a job",
)
async def close_employer_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobStatusUpdateResponse:
    """
    Close a job (stops accepting new applications).

    Transition: **published → closed** (or draft → closed).
    Closed jobs cannot be edited or re-opened.
    """
    _require_employer(current_user)

    try:
        job = await close_job(db, job_id=job_id, employer_id=current_user.id)
    except ValueError as exc:
        _map_job_error(exc)

    return JobStatusUpdateResponse(
        job_id=job.id,
        status=job.status,
        message="Job closed successfully",
    )


# ── DELETE /employer/jobs/{job_id} ────────────────────────────────────────────

@router.delete(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a draft job",
)
async def delete_employer_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Hard-delete a job in **draft** status.

    Published and closed jobs cannot be deleted (close them first, then
    contact support if removal from the DB is needed).
    """
    _require_employer(current_user)

    try:
        await delete_job(db, job_id=job_id, employer_id=current_user.id)
    except ValueError as exc:
        _map_job_error(exc)

    return {"message": "Job deleted successfully", "job_id": str(job_id)}
