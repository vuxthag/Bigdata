"""
routers/employer_company.py
============================
Employer company management endpoints.

Routes
------
POST /api/v1/employer/company           — create company (once per employer)
GET  /api/v1/employer/company/me        — get my company
PUT  /api/v1/employer/company/me        — update my company
POST /api/v1/employer/company/logo      — upload company logo (local storage)

Auth: JWT required, role must be 'employer'.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.company_schema import (
    CompanyCreate,
    CompanyCreateResponse,
    CompanyResponse,
    CompanyUpdate,
    LogoUploadResponse,
)
from app.services.auth_service import get_current_user
from app.services.company_service import (
    create_company,
    get_my_company,
    update_company,
    update_logo_url,
)

router = APIRouter(prefix="/employer/company", tags=["Employer — Company"])

# Logo storage directory (relative to project; mount as volume in production)
LOGO_DIR = Path(os.getenv("LOGO_UPLOAD_DIR", "/tmp/logos"))
ALLOWED_LOGO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_LOGO_SIZE_MB = 5


# ── Guards ────────────────────────────────────────────────────────────────────

def _require_employer(current_user: User) -> User:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can access this endpoint",
        )
    return current_user


# ── POST /employer/company ────────────────────────────────────────────────────

@router.post(
    "",
    response_model=CompanyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create my company profile",
)
async def create_my_company(
    body: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyCreateResponse:
    """
    Create a company profile for the authenticated employer.

    Each employer may have **only one** company. Returns 409 if one already exists.
    """
    _require_employer(current_user)

    try:
        company = await create_company(
            db,
            owner_id=current_user.id,
            name=body.name,
            description=body.description,
            industry=body.industry,
            size=body.size,
            location=body.location,
            website=body.website,
        )
    except ValueError as exc:
        if str(exc) == "already_has_company":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have a company. Use PUT /employer/company/me to update it.",
            )
        raise

    return CompanyCreateResponse(
        id=company.id,
        name=company.name,
        slug=company.slug,
    )


# ── GET /employer/company/me ──────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=CompanyResponse,
    summary="Get my company profile",
)
async def get_company(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyResponse:
    """
    Return the full company profile of the authenticated employer.
    Returns 404 if the employer has not created a company yet.
    """
    _require_employer(current_user)
    company = await get_my_company(db, owner_id=current_user.id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not created a company yet. Use POST /employer/company.",
        )
    return CompanyResponse.model_validate(company)


# ── PUT /employer/company/me ──────────────────────────────────────────────────

@router.put(
    "/me",
    response_model=CompanyResponse,
    summary="Update my company profile",
)
async def update_my_company(
    body: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyResponse:
    """
    Update mutable fields (name, description, industry, size, location, website).
    Only non-null fields in the request body are applied.
    """
    _require_employer(current_user)

    try:
        company = await update_company(
            db,
            owner_id=current_user.id,
            name=body.name,
            description=body.description,
            industry=body.industry,
            size=body.size,
            location=body.location,
            website=body.website,
        )
    except ValueError as exc:
        if str(exc) == "company_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found. Create one first with POST /employer/company.",
            )
        raise

    return CompanyResponse.model_validate(company)


# ── POST /employer/company/logo ───────────────────────────────────────────────

@router.post(
    "/logo",
    response_model=LogoUploadResponse,
    summary="Upload company logo",
)
async def upload_logo(
    file: UploadFile = File(..., description="Logo image (JPEG, PNG, WebP, GIF — max 5 MB)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LogoUploadResponse:
    """
    Upload a company logo.

    - Validates content type and size.
    - Stores the file on disk (configure `LOGO_UPLOAD_DIR` env var for production path).
    - Returns the public URL path.
    """
    _require_employer(current_user)

    # Validate content type
    if file.content_type not in ALLOWED_LOGO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: JPEG, PNG, WebP, GIF",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_LOGO_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Logo too large. Maximum size is {MAX_LOGO_SIZE_MB} MB.",
        )

    # Persist to disk
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    ext = (file.filename or "logo.jpg").rsplit(".", 1)[-1].lower()
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    dest = LOGO_DIR / filename
    dest.write_bytes(content)

    # Build a relative URL (serve via static files or CDN in production)
    logo_url = f"/static/logos/{filename}"

    try:
        await update_logo_url(db, owner_id=current_user.id, logo_url=logo_url)
    except ValueError as exc:
        if str(exc) == "company_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Create a company first before uploading a logo.",
            )
        raise

    return LogoUploadResponse(logo_url=logo_url)
