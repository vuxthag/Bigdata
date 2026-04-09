"""
routers/jobs.py
===============
Job descriptions: list, get, and create endpoints.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.ml.preprocessing import clean_text
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobCreate, JobListResponse, JobResponse
from app.services.auth_service import get_current_user
from app.services.embedding_service import embedding_service

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
):
    """List active jobs with optional title search and pagination."""
    query = select(Job).where(Job.is_active == True)
    count_query = select(func.count(Job.id)).where(Job.is_active == True)

    if search:
        query = query.where(Job.position_title.ilike(f"%{search}%"))
        count_query = count_query.where(Job.position_title.ilike(f"%{search}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a single job by ID."""
    result = await db.execute(select(Job).where(Job.id == job_id, Job.is_active == True))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResponse.model_validate(job)


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    body: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new job description (requires authentication)."""
    cleaned = clean_text(body.description)
    embedding_vec = embedding_service.encode(cleaned)

    job = Job(
        position_title=body.position_title,
        description=body.description,
        cleaned_description=cleaned,
        embedding=embedding_vec.tolist(),
        source="user",
        created_by=current_user.id,
    )
    db.add(job)
    await db.flush()
    await db.commit()
    await db.refresh(job)
    return JobResponse.model_validate(job)


@router.post("/upload", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def upload_job(
    body: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a new job description (alias for POST /jobs)."""
    return await create_job(body, db, current_user)


@router.delete("/{job_id}", status_code=status.HTTP_200_OK)
async def delete_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a job (set is_active = False)."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    job.is_active = False
    await db.commit()
    return {"message": "Job deleted successfully"}
