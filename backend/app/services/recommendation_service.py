"""
services/recommendation_service.py
====================================
Core recommendation logic.

Phase 4 upgrade: recommend_by_cv() now delegates to ranking_service for
multi-signal scoring (cosine + skill_overlap + interaction_bonus + yoe_match).
Response schema is unchanged — similarity_score is the composite final_score.
"""
from __future__ import annotations

import uuid
from typing import List

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cv import CV
from app.models.interaction import InteractionAction, UserInteraction
from app.models.job import Job
from app.schemas.recommendation import RecommendedJob
from app.services.embedding_service import embedding_service


async def recommend_by_cv(
    cv_id: uuid.UUID,
    db: AsyncSession,
    top_n: int = 5,
) -> List[RecommendedJob]:
    """
    Recommend top-N jobs most similar to a given CV.

    Phase 4: uses multi-signal AI ranking (cosine + skill + interaction + yoe).
    Falls back to pure cosine if ranking_service fails.
    """
    try:
        from app.services.ranking_service import rank_jobs_for_candidate
        ranked = await rank_jobs_for_candidate(cv_id=cv_id, db=db, top_n=top_n)
        return [
            RecommendedJob(
                job_id=r.job_id,
                position_title=r.position_title,
                description_preview=r.description_preview,
                similarity_score=r.final_score,   # composite score in [0, 1]
            )
            for r in ranked
        ]
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            f"[Recommend] Multi-signal ranking failed, falling back to cosine: {exc}"
        )
        return await _recommend_by_cv_cosine(cv_id, db, top_n)


async def _recommend_by_cv_cosine(
    cv_id: uuid.UUID,
    db: AsyncSession,
    top_n: int = 5,
) -> List[RecommendedJob]:
    """Fallback: pure pgvector cosine similarity (original implementation)."""
    result = await db.execute(select(CV).where(CV.id == cv_id))
    cv = result.scalar_one_or_none()
    if cv is None or cv.embedding is None:
        return []

    query = text(
        """
        SELECT id, position_title, description,
               1 - (embedding <=> CAST(:embedding AS vector)) AS similarity_score
        FROM job_descriptions
        WHERE is_active = true AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :limit
        """
    )
    embedding_str = "[" + ",".join(str(x) for x in cv.embedding) + "]"
    rows = await db.execute(query, {"embedding": embedding_str, "limit": top_n})
    jobs = rows.fetchall()

    return [
        RecommendedJob(
            job_id=row.id,
            position_title=row.position_title,
            description_preview=row.description[:200],
            similarity_score=round(max(0.0, min(1.0, float(row.similarity_score))), 4),
        )
        for row in jobs
    ]



async def recommend_by_title(
    job_title: str,
    db: AsyncSession,
    top_n: int = 5,
) -> List[RecommendedJob]:
    """
    Find a job matching the title, then recommend similar jobs via vector search.
    """
    # Find a job matching the title (case-insensitive partial match)
    result = await db.execute(
        select(Job).where(
            Job.position_title.ilike(f"%{job_title}%"),
            Job.is_active.is_(True),
            Job.embedding.isnot(None),
        ).limit(1)
    )
    ref_job = result.scalar_one_or_none()

    if ref_job is None:
        # Fallback: encode the title directly and search
        emb = embedding_service.encode(job_title)
        embedding_str = "[" + ",".join(str(x) for x in emb.tolist()) + "]"
    else:
        embedding_str = "[" + ",".join(str(x) for x in ref_job.embedding) + "]"

    query = text(
        """
        SELECT id, position_title, description,
               1 - (embedding <=> CAST(:embedding AS vector)) AS similarity_score
        FROM job_descriptions
        WHERE is_active = true AND embedding IS NOT NULL
              AND (:exclude_id IS NULL OR id != CAST(:exclude_id AS uuid))
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :limit
        """
    )
    rows = await db.execute(
        query,
        {
            "embedding": embedding_str,
            "exclude_id": str(ref_job.id) if ref_job else None,
            "limit": top_n,
        },
    )

    return [
        RecommendedJob(
            job_id=row.id,
            position_title=row.position_title,
            description_preview=row.description[:200],
            similarity_score=round(max(0.0, min(1.0, float(row.similarity_score))), 4),
        )
        for row in rows.fetchall()
    ]


async def log_interaction(
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    action: str,
    db: AsyncSession,
    cv_id: uuid.UUID | None = None,
    similarity_score: float | None = None,
) -> UserInteraction:
    """Insert a user interaction record into the DB."""
    interaction = UserInteraction(
        user_id=user_id,
        job_id=job_id,
        cv_id=cv_id,
        action=InteractionAction(action),
        similarity_score=similarity_score,
        is_trained=False,
    )
    db.add(interaction)
    await db.flush()
    return interaction
