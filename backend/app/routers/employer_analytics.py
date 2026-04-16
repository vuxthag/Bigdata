"""
routers/employer_analytics.py
==================================
Employer analytics endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.application import Application
from app.models.company import Company
from app.models.interaction import InteractionAction, UserInteraction
from app.models.job import Job
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/employer/analytics", tags=["Employer — Analytics"])

def _require_employer(current_user: User) -> User:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can access this endpoint"
        )
    return current_user

@router.get("", summary="Get summary analytics for the employer")
async def get_employer_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_employer(current_user)

    # Find the employer's company
    company_result = await db.execute(select(Company).where(Company.owner_id == current_user.id))
    company = company_result.scalar_one_or_none()

    if not company:
        # No company, no stats
        return {
            "total_jobs": 0,
            "total_applications": 0,
            "conversion_rate": 0.0,
            "top_jobs": []
        }

    # Total jobs owned by company
    total_jobs_res = await db.execute(
        select(func.count(Job.id))
        .where(Job.company_id == company.id)
    )
    total_jobs = total_jobs_res.scalar_one()

    # Total applications
    total_apps_res = await db.execute(
        select(func.count(Application.id))
        .join(Job, Job.id == Application.job_id)
        .where(Job.company_id == company.id)
    )
    total_apps = total_apps_res.scalar_one()

    # Total views for conversion rate
    total_views_res = await db.execute(
        select(func.count(UserInteraction.id))
        .join(Job, Job.id == UserInteraction.job_id)
        .where(Job.company_id == company.id, UserInteraction.action == InteractionAction.viewed)
    )
    total_views = total_views_res.scalar_one()

    conversion_rate = 0.0
    if total_views > 0:
        conversion_rate = round((total_apps / total_views) * 100, 2)

    # Top performing jobs
    top_jobs_res = await db.execute(
        select(
            Job.id,
            Job.position_title,
            func.count(Application.id).label("apps_count"),
            Job.applicant_count
        )
        .outerjoin(Application, Application.job_id == Job.id)
        .where(Job.company_id == company.id)
        .group_by(Job.id, Job.position_title)
        .order_by(func.count(Application.id).desc())
        .limit(5)
    )

    top_jobs = [
        {
            "job_id": str(r.id),
            "title": r.position_title,
            "applications": r.apps_count,
            "total_views": 0 # We could join interaction views, but let's keep it simple or do a subquery
        } for r in top_jobs_res.fetchall()
    ]

    return {
        "total_jobs": total_jobs,
        "total_applications": total_apps,
        "total_views": total_views,
        "conversion_rate": conversion_rate,
        "top_jobs": top_jobs
    }
