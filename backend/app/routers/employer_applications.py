"""
routers/employer_applications.py
==================================
Employer-facing application endpoints.

Routes
------
GET   /api/v1/employer/applications/{job_id}               — list applicants for a job
PATCH /api/v1/employer/applications/{application_id}/status — update application status

Auth: JWT required, role must be 'employer'.
The employer must OWN the job (via companies.owner_id == current_user.id).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.application_schema import (
    CandidateSummary,
    EmployerApplicationItem,
    EmployerApplicationListResponse,
    UpdateStatusRequest,
    UpdateStatusResponse,
)
from app.services.application_service import (
    get_employer_applications,
    update_application_status,
)
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/employer/applications", tags=["Employer — Applications"])


# ── Guards ────────────────────────────────────────────────────────────────────

def _require_employer(current_user: User) -> User:
    """Raise 403 if the authenticated user is not an employer."""
    if current_user.role != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can access this endpoint",
        )
    return current_user


# ── GET /employer/applications/{job_id} ───────────────────────────────────────

@router.get(
    "/{job_id}",
    response_model=EmployerApplicationListResponse,
    summary="List applicants for a specific job",
)
async def list_applications_for_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployerApplicationListResponse:
    """
    Return all applications for the given job, ordered newest-first.

    - **403** if caller is not an employer or does not own the job
    - **404** if the job does not exist

    The `match_score` field is reserved for Phase 3 (ML scoring) and is
    always `null` at this stage.
    """
    _require_employer(current_user)

    try:
        raw_items = await get_employer_applications(
            db,
            job_id=job_id,
            employer_id=current_user.id,
        )
    except ValueError as exc:
        _map_service_error(exc)

    items = [
        EmployerApplicationItem(
            application_id=row["application_id"],
            candidate=CandidateSummary(
                id=row["candidate"]["id"],
                name=row["candidate"]["name"],
                email=row["candidate"]["email"],
            ),
            cv_id=row["cv_id"],
            status=row["status"],
            applied_at=row["applied_at"],
            cover_letter=row["cover_letter"],
            note=row["note"],
            match_score=row["match_score"],
        )
        for row in raw_items
    ]

    return EmployerApplicationListResponse(
        items=items,
        total=len(items),
        job_id=job_id,
    )


# ── PATCH /employer/applications/{application_id}/status ─────────────────────

@router.patch(
    "/{application_id}/status",
    response_model=UpdateStatusResponse,
    summary="Update the status of an application",
)
async def update_status(
    application_id: uuid.UUID,
    body: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UpdateStatusResponse:
    """
    Move an application through the hiring pipeline.

    **Allowed status transitions:**
    ```
    applied  → reviewed | rejected
    reviewed → interview | rejected
    interview → offered | rejected
    offered  → hired | rejected
    rejected → (terminal)
    hired    → (terminal)
    ```

    - **403** if caller is not an employer or does not own the job
    - **404** if the application does not exist
    - **400** if the status transition is not allowed
    """
    _require_employer(current_user)

    try:
        updated_app = await update_application_status(
            db,
            application_id=application_id,
            employer_id=current_user.id,
            new_status=body.status,
        )
    except ValueError as exc:
        _map_service_error(exc)

    return UpdateStatusResponse(
        message="Status updated successfully",
        application_id=updated_app.id,
        new_status=updated_app.status.value if hasattr(updated_app.status, "value") else updated_app.status,
    )


# ── Error mapping ─────────────────────────────────────────────────────────────

def _map_service_error(exc: ValueError) -> None:
    """Convert service-layer ValueError codes to HTTPException. Never returns."""
    code = str(exc)
    if code == "job_not_found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if code == "application_not_found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if code == "forbidden":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource",
        )
    if code == "invalid_transition":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid status transition. "
                "Allowed flow: applied→reviewed→interview→offered→hired (rejected at any step)"
            ),
        )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Unexpected error: {code}",
    )
