"""
services/ranking_service.py
============================
AI Ranking Service — Candidate-Only Platform.

Single public function:

  rank_jobs_for_candidate(cv_id, db, top_n, weights?)
      → list[RankedJob]  sorted by multi-signal match_score DESC

Score formula
─────────────
  final_score = w1·cosine_similarity
              + w2·skill_overlap
              + w3·interaction_bonus
              + w4·yoe_match          (clamped to [0, 1])

Default weights: w1=0.60, w2=0.20, w3=0.15, w4=0.05
"""
from __future__ import annotations

import logging
import uuid

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.feature_engine import (
    build_interaction_bonus,
    extract_skills,
    skill_overlap,
    years_of_experience,
)
from app.models.cv import CV
from app.models.interaction import UserInteraction
from app.schemas.ranking_schema import RankedJob, ScoreBreakdown

logger = logging.getLogger(__name__)

# ── Default scoring weights ───────────────────────────────────────────────────
DEFAULT_WEIGHTS: dict[str, float] = {
    "cosine":      0.60,
    "skill":       0.20,
    "interaction": 0.15,
    "yoe":         0.05,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _vec_to_str(embedding: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity — SBERT vectors are already L2-normalised."""
    score = float(np.dot(a, b))
    return float(np.clip(score, 0.0, 1.0))


def _yoe_compatibility(cv_yoe: float, jd_yoe: float) -> float:
    """
    Score how well the candidate's YOE matches the JD requirement.

    If the JD mentions no YOE requirement → neutral score (0.5).
    If CV over-qualifies → 1.0; if under-qualifies → linear decay.
    """
    if jd_yoe <= 0:
        return 0.5   # no requirement stated — neutral
    if cv_yoe >= jd_yoe:
        return 1.0
    return float(np.clip(cv_yoe / jd_yoe, 0.0, 1.0))


def _composite_score(
    cosine: float,
    skill: float,
    interaction: float,
    yoe: float,
    weights: dict[str, float],
) -> float:
    total_w = sum(weights.values()) or 1.0
    score = (
        weights.get("cosine",       0.60) * cosine
        + weights.get("skill",      0.20) * skill
        + weights.get("interaction", 0.15) * interaction
        + weights.get("yoe",        0.05) * yoe
    ) / total_w
    return float(np.clip(score, 0.0, 1.0))


# ── Main public function ──────────────────────────────────────────────────────

async def rank_jobs_for_candidate(
    cv_id: uuid.UUID,
    db: AsyncSession,
    top_n: int = 10,
    weights: dict[str, float] | None = None,
) -> list[RankedJob]:
    """
    Multi-signal job recommendation for a candidate.

    Steps:
    1. Load CV embedding + raw text
    2. Load candidate's interaction history
    3. pgvector ANN pre-filter: top-200 nearest jobs by cosine distance
    4. Re-rank with composite score (cosine + skill + interaction + yoe)
    5. Return top_n results sorted by score DESC

    Returns empty list if CV has no embedding yet.
    """
    weights = weights or DEFAULT_WEIGHTS

    # 1. Fetch CV
    cv_result = await db.execute(select(CV).where(CV.id == cv_id))
    cv: CV | None = cv_result.scalar_one_or_none()
    if cv is None or cv.embedding is None:
        logger.warning(f"[Ranking] CV {cv_id} not found or has no embedding")
        return []

    cv_emb    = np.array(cv.embedding, dtype=np.float32)
    cv_text   = cv.raw_text or ""
    cv_skills = extract_skills(cv_text)
    cv_yoe    = years_of_experience(cv_text)

    # 2. Fetch candidate's interaction history
    int_result = await db.execute(
        select(UserInteraction.job_id, UserInteraction.action)
        .where(UserInteraction.user_id == cv.user_id)
    )
    interactions = [
        {"job_id": str(r.job_id), "action": str(r.action)}
        for r in int_result.all()
    ]

    # 3. pgvector ANN pre-filter — top 200 by cosine distance (no status filter)
    from sqlalchemy import text as sa_text
    emb_str = _vec_to_str(cv.embedding)
    pre_filter_stmt = sa_text(
        """
        SELECT id, position_title, description, embedding,
               company, location, skills, salary_min, salary_max, job_type
        FROM job_descriptions
        WHERE is_active = true
          AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT 200
        """
    )
    jd_rows = (await db.execute(pre_filter_stmt, {"emb": emb_str})).all()

    # 4. Re-rank with composite score
    scored: list[tuple[float, RankedJob]] = []

    for row in jd_rows:
        jd_emb    = np.array(row.embedding, dtype=np.float32)
        jd_text   = (row.description or "") + " " + (row.position_title or "")
        jd_skills = extract_skills(jd_text)
        jd_yoe    = years_of_experience(jd_text)

        cosine      = _cosine(cv_emb, jd_emb)
        skill_sc    = skill_overlap(cv_skills, jd_skills)
        interaction = build_interaction_bonus(interactions, str(row.id))
        yoe_sc      = _yoe_compatibility(cv_yoe, jd_yoe)
        final       = _composite_score(cosine, skill_sc, interaction, yoe_sc, weights)

        breakdown = ScoreBreakdown(
            cosine_similarity = round(cosine,      4),
            skill_overlap     = round(skill_sc,    4),
            interaction_bonus = round(interaction, 4),
            years_match       = round(yoe_sc,      4),
        )

        scored.append((final, RankedJob(
            job_id              = row.id,
            position_title      = row.position_title,
            description_preview = (row.description or "")[:250],
            final_score         = round(final, 4),
            score_breakdown     = breakdown,
            company             = row.company,
            location            = row.location,
            skills              = list(row.skills or []),
            salary_min          = row.salary_min,
            salary_max          = row.salary_max,
        )))

    # 5. Filter >= 50%, Sort descending and return top_n
    filtered_scored = [(s, r) for s, r in scored if s >= 0.5]
    filtered_scored.sort(key=lambda t: t[0], reverse=True)
    return [r for _, r in filtered_scored[:top_n]]
