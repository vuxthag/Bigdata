"""
routers/candidate_applications.py
===================================
Candidate-facing application endpoints.

Routes
------
POST /api/v1/candidate/applications          — apply to a published job
GET  /api/v1/candidate/applications          — list own applications with job/company info

Auth: JWT required, role must be 'candidate'.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.application_schema import (
    ApplyRequest,
    ApplyResponse,
    CandidateApplicationItem,
    CandidateApplicationListResponse,
    JobSummary,
)
from app.services.application_service import apply_to_job, get_candidate_applications
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/candidate/applications", tags=["Candidate — Applications"])


# ── Guards ────────────────────────────────────────────────────────────────────

def _require_candidate(current_user: User) -> User:
    """Raise 403 if the authenticated user is not a candidate."""
    if current_user.role != "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can access this endpoint",
        )
    return current_user


# ── POST /candidate/applications ──────────────────────────────────────────────

@router.post(
    "",
    response_model=ApplyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply to a published job",
)
async def apply_job(
    body: ApplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplyResponse:
    """
    Submit an application for a published job.

    - **job_id**: UUID of the target job (must be `published`)
    - **cv_id**: optional UUID of a CV to attach
    - **cover_letter**: optional text up to 5 000 characters

    Errors:
    - 403 if caller is not a `candidate`
    - 404 if the job does not exist
    - 400 if the job is not `published`
    - 409 if the candidate has already applied to this job
    """
    _require_candidate(current_user)

    try:
        application = await apply_to_job(
            db,
            candidate_id=current_user.id,
            job_id=body.job_id,
            cv_id=body.cv_id,
            cover_letter=body.cover_letter,
        )
    except ValueError as exc:
        _map_service_error(exc)

    return ApplyResponse(
        message="Application submitted successfully",
        application_id=application.id,
    )


# ── GET /candidate/applications ───────────────────────────────────────────────

@router.get(
    "",
    response_model=CandidateApplicationListResponse,
    summary="List my applications",
)
async def list_my_applications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CandidateApplicationListResponse:
    """
    Return all applications submitted by the authenticated candidate,
    enriched with job title and company name, ordered newest first.
    """
    _require_candidate(current_user)

    raw_items = await get_candidate_applications(db, candidate_id=current_user.id)

    items = [
        CandidateApplicationItem(
            application_id=row["application_id"],
            job=JobSummary(
                id=row["job"]["id"],
                title=row["job"]["title"],
                company_name=row["job"]["company_name"],
                status=row["job"]["status"],
            ),
            status=row["status"],
            applied_at=row["applied_at"],
            cover_letter=row["cover_letter"],
        )
        for row in raw_items
    ]

    return CandidateApplicationListResponse(items=items, total=len(items))


# ── Error mapping ─────────────────────────────────────────────────────────────

def _map_service_error(exc: ValueError) -> None:
    """Convert service-layer ValueError codes to HTTPException. Never returns."""
    code = str(exc)
    if code == "job_not_found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if code == "job_not_published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is not published and cannot accept applications",
        )
    if code == "already_applied":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied to this job",
        )
    # Should never reach here, but be safe
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Unexpected error: {code}",
    )
