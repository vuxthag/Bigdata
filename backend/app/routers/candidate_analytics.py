"""
routers/candidate_analytics.py
==================================
Candidate analytics endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.application import Application, ApplicationStatus
from app.models.interaction import InteractionAction, UserInteraction
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/candidate/analytics", tags=["Candidate — Analytics"])

@router.get("", summary="Get summary analytics for the candidate")
async def get_candidate_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can access this endpoint"
        )

    # 1. Jobs applied
    jobs_applied_res = await db.execute(
        select(func.count(Application.id))
        .where(Application.candidate_id == current_user.id)
    )
    total_applied = jobs_applied_res.scalar_one()

    # 2. Success rate (Hired + Offered / Total Applied)
    success_res = await db.execute(
        select(func.count(Application.id))
        .where(
            Application.candidate_id == current_user.id,
            Application.status.in_([ApplicationStatus.hired, ApplicationStatus.offered])
        )
    )
    total_success = success_res.scalar_one()
    
    success_rate = 0.0
    if total_applied > 0:
        success_rate = round((total_success / total_applied) * 100, 2)

    # 3. Recommended vs Applied
    # How many of the applied jobs did the user view first?
    # Alternatively: ratio of total recommended (viewed) to applied.
    # We will count how many Application.job_id are also in UserInteraction for this user with action='viewed'
    recommended_applied_res = await db.execute(
        select(func.count(Application.id))
        .where(
            Application.candidate_id == current_user.id,
            Application.job_id.in_(
                select(UserInteraction.job_id)
                .where(UserInteraction.user_id == current_user.id, UserInteraction.action == InteractionAction.viewed)
            )
        )
    )
    recommended_and_applied = recommended_applied_res.scalar_one()

    # Total viewed
    total_viewed_res = await db.execute(
        select(func.count(UserInteraction.id))
        .where(UserInteraction.user_id == current_user.id, UserInteraction.action == InteractionAction.viewed)
    )
    total_viewed = total_viewed_res.scalar_one()

    return {
        "total_applied": total_applied,
        "success_rate": success_rate,
        "total_success": total_success,
        "recommended_and_applied": recommended_and_applied,
        "total_viewed": total_viewed
    }
