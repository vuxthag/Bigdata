"""
routers/system_analytics.py
==================================
System-wide analytics endpoints (Admin).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.application import Application
from app.models.job import Job
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/system/analytics", tags=["System — Analytics"])

def _require_admin(current_user: User) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    return current_user

@router.get("", summary="Get system-wide analytics")
async def get_system_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    total_users_res = await db.execute(select(func.count(User.id)))
    total_users = total_users_res.scalar_one()

    total_jobs_res = await db.execute(select(func.count(Job.id)))
    total_jobs = total_jobs_res.scalar_one()

    active_jobs_res = await db.execute(select(func.count(Job.id)).where(Job.is_active == True, Job.status == "published"))
    active_jobs = active_jobs_res.scalar_one()

    # Daily applications (last 7 days)
    seven_days_ago = datetime.now(tz=timezone.utc) - timedelta(days=7)
    daily_apps_res = await db.execute(
        select(
            func.date(Application.applied_at).label("date"),
            func.count(Application.id).label("count")
        )
        .where(Application.applied_at >= seven_days_ago)
        .group_by(func.date(Application.applied_at))
        .order_by(func.date(Application.applied_at))
    )
    
    daily_applications = [
        {"date": str(row.date), "count": row.count}
        for row in daily_apps_res.fetchall()
    ]

    return {
        "total_users": total_users,
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "daily_applications": daily_applications,
        "model_version": getattr(current_user, "dummy_avoidance", "v2.1") # Optional just to make UI look nice
    }
