"""
routers/cvs.py
==============
CV upload, list, and delete endpoints.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.ml.preprocessing import clean_text
from app.models.cv import CV
from app.models.user import User
from app.schemas.cv import CVListResponse, CVResponse
from app.services.auth_service import get_current_user
from app.services.cv_parser import parse_cv_file, validate_file_size
from app.services.embedding_service import embedding_service

router = APIRouter(prefix="/cvs", tags=["CVs"])


@router.post("/upload", response_model=CVResponse, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a CV (PDF or DOCX), extract text, encode embedding, store in DB."""
    file_bytes = await file.read()

    # Validate file size
    if not validate_file_size(file_bytes):
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max allowed: {10} MB",
        )

    # Parse text
    try:
        raw_text = parse_cv_file(file.filename, file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract text from the file. Please check the file content.",
        )

    # Clean text and encode embedding
    cleaned = clean_text(raw_text)
    embedding_vec = embedding_service.encode(cleaned)

    cv = CV(
        user_id=current_user.id,
        filename=file.filename,
        raw_text=raw_text,
        cleaned_text=cleaned,
        embedding=embedding_vec.tolist(),
        file_size_kb=len(file_bytes) // 1024,
    )
    db.add(cv)
    await db.flush()
    await db.commit()
    await db.refresh(cv)

    return CVResponse.model_validate(cv)


@router.get("", response_model=CVListResponse)
async def list_cvs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all CVs uploaded by the current user."""
    result = await db.execute(
        select(CV).where(CV.user_id == current_user.id).order_by(CV.uploaded_at.desc())
    )
    cvs = result.scalars().all()
    return CVListResponse(items=[CVResponse.model_validate(c) for c in cvs], total=len(cvs))


@router.get("/{cv_id}", response_model=CVResponse)
async def get_cv(
    cv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single CV by ID (must be owned by current user)."""
    result = await db.execute(select(CV).where(CV.id == cv_id, CV.user_id == current_user.id))
    cv = result.scalar_one_or_none()
    if cv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
    return CVResponse.model_validate(cv)


@router.delete("/{cv_id}", status_code=status.HTTP_200_OK)
async def delete_cv(
    cv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a CV owned by the current user."""
    result = await db.execute(select(CV).where(CV.id == cv_id, CV.user_id == current_user.id))
    cv = result.scalar_one_or_none()
    if cv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")

    await db.delete(cv)
    await db.commit()
    return {"message": "CV deleted successfully"}
