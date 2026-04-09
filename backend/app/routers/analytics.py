"""
routers/analytics.py
=====================
Analytics endpoints for dashboard statistics, charts, and trends.
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


@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Comprehensive dashboard data for the analytics page."""
    # Total counts
    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    total_cvs = (await db.execute(select(func.count(CV.id)))).scalar_one()
    total_jobs = (await db.execute(
        select(func.count(Job.id)).where(Job.is_active.is_(True))
    )).scalar_one()
    total_interactions = (await db.execute(
        select(func.count(UserInteraction.id))
    )).scalar_one()
    total_recommendations = (await db.execute(
        select(func.count(UserInteraction.id)).where(
            UserInteraction.action == InteractionAction.viewed
        )
    )).scalar_one()

    # Average similarity
    avg_sim_result = (await db.execute(
        select(func.avg(UserInteraction.similarity_score)).where(
            UserInteraction.similarity_score.isnot(None)
        )
    )).scalar_one()
    avg_similarity = round(float(avg_sim_result or 0.0), 4)

    # Interaction breakdown
    action_counts = {}
    for action in InteractionAction:
        count = (await db.execute(
            select(func.count(UserInteraction.id)).where(
                UserInteraction.action == action
            )
        )).scalar_one()
        action_counts[action.value] = count

    # Most active users (top 5)
    active_users_result = await db.execute(
        select(
            User.id,
            User.email,
            User.full_name,
            func.count(UserInteraction.id).label("activity_count"),
        )
        .join(UserInteraction, UserInteraction.user_id == User.id)
        .group_by(User.id, User.email, User.full_name)
        .order_by(func.count(UserInteraction.id).desc())
        .limit(5)
    )
    most_active_users = [
        {
            "user_id": str(row.id),
            "email": row.email,
            "full_name": row.full_name,
            "activity_count": row.activity_count,
        }
        for row in active_users_result.fetchall()
    ]

    # CV upload trend (last 7 days)
    seven_days_ago = datetime.now(tz=timezone.utc) - timedelta(days=7)
    cv_trend_result = await db.execute(
        select(
            func.date(CV.uploaded_at).label("date"),
            func.count(CV.id).label("count"),
        )
        .where(CV.uploaded_at >= seven_days_ago)
        .group_by(func.date(CV.uploaded_at))
        .order_by(func.date(CV.uploaded_at))
    )
    cv_upload_trend = [
        {"date": str(row.date), "count": row.count}
        for row in cv_trend_result.fetchall()
    ]

    # Job upload trend (last 7 days)
    job_trend_result = await db.execute(
        select(
            func.date(Job.created_at).label("date"),
            func.count(Job.id).label("count"),
        )
        .where(Job.created_at >= seven_days_ago)
        .group_by(func.date(Job.created_at))
        .order_by(func.date(Job.created_at))
    )
    job_upload_trend = [
        {"date": str(row.date), "count": row.count}
        for row in job_trend_result.fetchall()
    ]

    return {
        "total_users": total_users,
        "total_cvs": total_cvs,
        "total_jobs": total_jobs,
        "total_interactions": total_interactions,
        "total_recommendations": total_recommendations,
        "avg_similarity_score": avg_similarity,
        "action_counts": action_counts,
        "most_active_users": most_active_users,
        "cv_upload_trend": cv_upload_trend,
        "job_upload_trend": job_upload_trend,
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


@router.get("/similarity")
async def similarity_alias(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Alias for /similarity-distribution."""
    return await similarity_distribution(db, current_user)


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


@router.get("/top-jobs")
async def top_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return top recommended jobs (most interactions)."""
    result = await db.execute(
        select(
            Job.id,
            Job.position_title,
            func.count(UserInteraction.id).label("interaction_count"),
            func.avg(UserInteraction.similarity_score).label("avg_score"),
        )
        .join(UserInteraction, UserInteraction.job_id == Job.id)
        .group_by(Job.id, Job.position_title)
        .order_by(func.count(UserInteraction.id).desc())
        .limit(10)
    )
    return [
        {
            "job_id": str(row.id),
            "title": row.position_title,
            "interaction_count": row.interaction_count,
            "avg_similarity": round(float(row.avg_score or 0), 4),
        }
        for row in result.fetchall()
    ]
