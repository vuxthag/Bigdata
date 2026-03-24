"""
routers/recommend.py
=====================
Recommendation endpoints: by CV, by title, and interaction feedback.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.cv import CV
from app.models.user import User
from app.schemas.recommendation import (
    InteractionCreate,
    RecommendByCVRequest,
    RecommendByTitleRequest,
    RecommendResponse,
)
from app.services.auth_service import get_current_user
from app.services.continual_learning import continual_learner
from app.services.recommendation_service import log_interaction, recommend_by_cv, recommend_by_title

router = APIRouter(prefix="/recommend", tags=["Recommendations"])


@router.post("/by-cv", response_model=RecommendResponse)
async def recommend_by_cv_endpoint(
    body: RecommendByCVRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recommend jobs matching the user's uploaded CV."""
    # Ownership check
    result = await db.execute(
        select(CV).where(CV.id == body.cv_id, CV.user_id == current_user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")

    recommendations = await recommend_by_cv(body.cv_id, db, body.top_n)

    # Auto-log "viewed" interactions
    for rec in recommendations:
        await log_interaction(
            user_id=current_user.id,
            job_id=rec.job_id,
            action="viewed",
            db=db,
            cv_id=body.cv_id,
            similarity_score=rec.similarity_score,
        )

    return RecommendResponse(
        query=str(body.cv_id),
        results=recommendations,
        model_version=continual_learner.get_model_version(),
    )


@router.post("/by-title", response_model=RecommendResponse)
async def recommend_by_title_endpoint(
    body: RecommendByTitleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recommend jobs similar to a given job title."""
    recommendations = await recommend_by_title(body.job_title, db, body.top_n)

    if not recommendations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No recommendations found for title: '{body.job_title}'",
        )

    return RecommendResponse(
        query=body.job_title,
        results=recommendations,
        model_version=continual_learner.get_model_version(),
    )


@router.post("/feedback", status_code=status.HTTP_200_OK)
async def feedback(
    body: InteractionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record user feedback (applied/saved/skipped) for continual learning."""
    await log_interaction(
        user_id=current_user.id,
        job_id=body.job_id,
        action=body.action,
        db=db,
        cv_id=body.cv_id,
        similarity_score=body.similarity_score,
    )
    return {"message": "Feedback recorded", "action": body.action}
