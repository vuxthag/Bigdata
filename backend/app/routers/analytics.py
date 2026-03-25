"""
routers/analytics.py
=====================
Analytics endpoints for dashboard statistics and charts.
Fix: removed unused imports (Float, case, cast) that cause ImportError.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.cv import CV
from app.models.interaction import InteractionAction, UserInteraction
from app.models.job import Job
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.continual_learning import continual_learner

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return dashboard statistics for the current user."""
    cv_count = await db.execute(
        select(func.count(CV.id)).where(CV.user_id == current_user.id)
    )
    total_cvs = cv_count.scalar_one()

    job_count = await db.execute(
        select(func.count(Job.id)).where(Job.is_active.is_(True))
    )
    total_jobs = job_count.scalar_one()

    viewed_count = await db.execute(
        select(func.count(UserInteraction.id)).where(
            UserInteraction.user_id == current_user.id,
            UserInteraction.action == InteractionAction.viewed,
        )
    )
    total_recommendations = viewed_count.scalar_one()

    avg_sim = await db.execute(
        select(func.avg(UserInteraction.similarity_score)).where(
            UserInteraction.user_id == current_user.id,
            UserInteraction.similarity_score.isnot(None),
        )
    )
    avg_similarity = round(float(avg_sim.scalar_one() or 0.0), 4)

    top_jobs_result = await db.execute(
        select(
            Job.id,
            Job.position_title,
            func.count(UserInteraction.id).label("match_count"),
        )
        .join(UserInteraction, UserInteraction.job_id == Job.id)
        .where(UserInteraction.user_id == current_user.id)
        .group_by(Job.id, Job.position_title)
        .order_by(func.count(UserInteraction.id).desc())
        .limit(5)
    )
    top_jobs = [
        {"job_id": str(row.id), "title": row.position_title, "match_count": row.match_count}
        for row in top_jobs_result.fetchall()
    ]

    return {
        "total_cvs": total_cvs,
        "total_jobs": total_jobs,
        "total_recommendations": total_recommendations,
        "avg_similarity_score": avg_similarity,
        "top_matched_jobs": top_jobs,
        "model_version": continual_learner.get_model_version(),
    }


@router.get("/similarity-distribution")
async def similarity_distribution(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return histogram of similarity scores in 0.1-wide bins."""
    result = await db.execute(
        select(UserInteraction.similarity_score).where(
            UserInteraction.user_id == current_user.id,
            UserInteraction.similarity_score.isnot(None),
        )
    )
    scores = [float(r[0]) for r in result.fetchall()]

    bins = [
        ("0.0-0.1", 0.0, 0.1), ("0.1-0.2", 0.1, 0.2), ("0.2-0.3", 0.2, 0.3),
        ("0.3-0.4", 0.3, 0.4), ("0.4-0.5", 0.4, 0.5), ("0.5-0.6", 0.5, 0.6),
        ("0.6-0.7", 0.6, 0.7), ("0.7-0.8", 0.7, 0.8), ("0.8-0.9", 0.8, 0.9),
        ("0.9-1.0", 0.9, 1.01),
    ]
    distribution = []
    for label, lo, hi in bins:
        count = sum(1 for s in scores if lo <= s < hi)
        distribution.append({"range": label, "count": count})

    return distribution


@router.get("/activity")
async def activity(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return interaction counts by day for the past 7 days."""
    seven_days_ago = datetime.now(tz=timezone.utc) - timedelta(days=7)

    result = await db.execute(
        select(
            func.date(UserInteraction.created_at).label("date"),
            UserInteraction.action,
            func.count(UserInteraction.id).label("count"),
        )
        .where(
            UserInteraction.user_id == current_user.id,
            UserInteraction.created_at >= seven_days_ago,
        )
        .group_by(func.date(UserInteraction.created_at), UserInteraction.action)
        .order_by(func.date(UserInteraction.created_at))
    )

    data: dict[str, dict] = {}
    for row in result.fetchall():
        day = str(row.date)
        if day not in data:
            data[day] = {"date": day, "applied": 0, "saved": 0, "skipped": 0, "viewed": 0}
        data[day][row.action.value] = row.count

    return sorted(data.values(), key=lambda x: x["date"])
