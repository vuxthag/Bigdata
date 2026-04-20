"""
services/ranking_service.py
============================
AI Ranking Service — Candidate-Only Platform.

Single public function:

  rank_jobs_for_candidate(cv_id, db, top_n, weights?)
      → list[RankedJob]  sorted by multi-signal match_score DESC

Score formula (Phase 5 — enhanced)
───────────────────────────────────
  final_score = w1·cosine_similarity
              + w2·skill_overlap
              + w3·interaction_bonus
              + w4·yoe_match
              + w5·level_match
              + w6·education_match    (clamped to [0, 1])

Default weights: w1=0.40, w2=0.30, w3=0.10, w4=0.08, w5=0.07, w6=0.05
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
)
from app.models.cv import CV
from app.models.interaction import UserInteraction
from app.schemas.ranking_schema import RankedJob, ScoreBreakdown
from app.services.cv_analyzer import (
    analyze_cv,
    build_jd_skill_pool,
    compute_job_match,
    extract_education,
)

logger = logging.getLogger(__name__)

# ── Default scoring weights (Phase 5 — rebalanced) ──────────────────────────
DEFAULT_WEIGHTS: dict[str, float] = {
    "cosine":      0.40,
    "skill":       0.30,
    "interaction": 0.10,
    "yoe":         0.08,
    "level":       0.07,
    "education":   0.05,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _vec_to_str(embedding: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"


def _parse_embedding(embedding_val) -> list[float]:
    """Parse embedding from various formats (list, string, numpy array)."""
    if embedding_val is None:
        return []
    if isinstance(embedding_val, list):
        return [float(x) for x in embedding_val]
    if isinstance(embedding_val, str):
        # Remove brackets and split by comma
        cleaned = embedding_val.strip("[]")
        if not cleaned:
            return []
        return [float(x) for x in cleaned.split(",")]
    # Handle numpy array or other sequence types
    return [float(x) for x in embedding_val]


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


def _level_compatibility(cv_level_hint: str | None, jd_level: str | None) -> float:
    """
    Score how well the candidate's seniority level matches the JD requirement.
    Returns 0.5 (neutral) if either side is unknown.
    """
    from app.services.cv_analyzer import JOB_LEVEL_ORDER
    if not cv_level_hint or not jd_level:
        return 0.5
    cv_rank = JOB_LEVEL_ORDER.get(cv_level_hint.lower().strip(), -1)
    jd_rank = JOB_LEVEL_ORDER.get(jd_level.lower().strip(), -1)
    if cv_rank < 0 or jd_rank < 0:
        return 0.5
    diff = cv_rank - jd_rank
    if diff >= 0:
        return 1.0
    return float(np.clip(1.0 + diff * 0.25, 0.0, 1.0))


def _education_compatibility(cv_edu: str | None, jd_edu: str | None) -> float:
    """
    Score education compatibility. Returns 0.5 if either side unknown.
    """
    from app.services.cv_analyzer import EDUCATION_LEVELS
    if not cv_edu or not jd_edu:
        return 0.5
    try:
        cv_rank = EDUCATION_LEVELS.index(cv_edu)
        jd_rank = EDUCATION_LEVELS.index(jd_edu)
    except ValueError:
        return 0.5
    if cv_rank >= jd_rank:
        return 1.0
    return float(np.clip(0.5 + (cv_rank - jd_rank) * 0.2, 0.0, 1.0))


def _enhanced_skill_overlap(
    cv_skills: set[str],
    jd_stored_skills: list[str] | None,
    jd_requirement: str | None,
    jd_description: str | None,
) -> float:
    """
    Compute skill overlap using:
    1. JD's stored skills array (from CSV/crawler)
    2. Skills extracted from job_requirement text
    3. Skills extracted from description text
    This gives much better coverage than extracting from description alone.
    """
    all_jd_skills: set[str] = set()
    if jd_stored_skills:
        all_jd_skills.update(s.lower().strip() for s in jd_stored_skills if s)
    if jd_requirement:
        all_jd_skills.update(extract_skills(jd_requirement))
    if jd_description:
        all_jd_skills.update(extract_skills(jd_description))

    if not cv_skills and not all_jd_skills:
        return 0.0
    union = cv_skills | all_jd_skills
    if not union:
        return 0.0
    return len(cv_skills & all_jd_skills) / len(union)


def _composite_score(
    cosine: float,
    skill: float,
    interaction: float,
    yoe: float,
    level: float,
    education: float,
    weights: dict[str, float],
) -> float:
    total_w = sum(weights.values()) or 1.0
    score = (
        weights.get("cosine",      0.40) * cosine
        + weights.get("skill",     0.30) * skill
        + weights.get("interaction", 0.10) * interaction
        + weights.get("yoe",       0.08) * yoe
        + weights.get("level",     0.07) * level
        + weights.get("education", 0.05) * education
    ) / total_w
    return float(np.clip(score, 0.0, 1.0))


# ── Feedback deltas ──────────────────────────────────────────────────────────
FEEDBACK_DELTAS: dict[str, float] = {
    "hired":    +0.20,
    "applied":  +0.15,
    "saved":    +0.10,
    "viewed":   +0.05,
    "skipped":  -0.05,
    "rejected": -0.15,
}

# ── Cache ────────────────────────────────────────────────────────────────────
_cache: dict[str, object] = {}


def invalidate_ranking_cache(job_id: uuid.UUID) -> None:
    """Remove all cached entries containing the given job_id."""
    keys_to_remove = [k for k in _cache if str(job_id) in k]
    for k in keys_to_remove:
        del _cache[k]


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
    1. Load CV embedding + raw text → structured CV analysis
    2. Load candidate's interaction history
    3. pgvector ANN pre-filter: top-200 nearest jobs by cosine distance
    4. Re-rank with 6-signal composite score
    5. Return top_n results sorted by score DESC

    Returns empty list if CV has no embedding yet.
    """
    weights = weights or DEFAULT_WEIGHTS

    # 1. Fetch CV and build structured profile
    cv_result = await db.execute(select(CV).where(CV.id == cv_id))
    cv: CV | None = cv_result.scalar_one_or_none()
    if cv is None or cv.embedding is None:
        logger.warning(f"[Ranking] CV {cv_id} not found or has no embedding")
        return []

    cv_emb  = np.array(cv.embedding, dtype=np.float32)
    cv_text = cv.raw_text or ""

    # 2. Fetch candidate's interaction history
    int_result = await db.execute(
        select(UserInteraction.job_id, UserInteraction.action)
        .where(UserInteraction.user_id == cv.user_id)
    )
    interactions = [
        {"job_id": str(r.job_id), "action": str(r.action)}
        for r in int_result.all()
    ]

    # 3. pgvector ANN pre-filter — top 200 by cosine distance
    from sqlalchemy import text as sa_text
    emb_str = _vec_to_str(cv.embedding)
    pre_filter_stmt = sa_text(
        """
        SELECT id, position_title, description, embedding,
               company, location, skills, salary_min, salary_max, job_type,
               job_requirement, years_of_experience, job_level, pretty_salary
        FROM job_descriptions
        WHERE is_active = true
          AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT 200
        """
    )
    jd_rows = (await db.execute(pre_filter_stmt, {"emb": emb_str})).all()

    # Build JD skill pool from ALL jobs first (for comprehensive CV skill extraction)
    jd_skill_pool = build_jd_skill_pool([list(r.skills or []) for r in jd_rows])

    # Also extract skills from JD descriptions to enrich the pool
    for row in jd_rows:
        if row.description:
            from app.ml.feature_engine import extract_skills as base_extract
            desc_skills = base_extract(row.description)
            jd_skill_pool.update(desc_skills)
        if row.job_requirement:
            from app.ml.feature_engine import extract_skills as base_extract
            req_skills = base_extract(row.job_requirement)
            jd_skill_pool.update(req_skills)

    # Now analyze CV with enriched skill pool
    cv_profile = analyze_cv(cv_text, jd_skill_pool)
    cv_skills_lower = {s.lower() for s in cv_profile.skills}

    # 4. Re-rank with enhanced composite score
    scored: list[tuple[float, RankedJob]] = []

    for row in jd_rows:
        jd_emb_list = _parse_embedding(row.embedding)
        if not jd_emb_list or len(jd_emb_list) < 10:
            logger.warning(f"[Ranking] Invalid embedding for job {row.id}, skipping")
            continue
        jd_emb = np.array(jd_emb_list, dtype=np.float32)

        # Use stored YOE from DB (much more reliable than regex from text)
        jd_yoe = float(row.years_of_experience or 0)

        cosine      = _cosine(cv_emb, jd_emb)
        skill_sc    = _enhanced_skill_overlap(
            cv_skills_lower, list(row.skills or []),
            row.job_requirement, row.description,
        )
        interaction = build_interaction_bonus(interactions, str(row.id))
        yoe_sc      = _yoe_compatibility(cv_profile.years_of_experience, jd_yoe)
        level_sc    = _level_compatibility(cv_profile.job_level_hint, row.job_level)

        # Education: extract from job requirement text
        jd_edu = extract_education(row.job_requirement or "")
        edu_sc = _education_compatibility(cv_profile.education_level, jd_edu)

        final = _composite_score(cosine, skill_sc, interaction, yoe_sc, level_sc, edu_sc, weights)

        # Per-job skill breakdown
        jd_match = compute_job_match(
            cv_profile,
            jd_skills=list(row.skills or []),
            jd_requirement=row.job_requirement,
            jd_description=row.description,
            jd_yoe=int(jd_yoe),
            jd_level=row.job_level,
        )

        breakdown = ScoreBreakdown(
            cosine_similarity = round(cosine,   4),
            skill_overlap     = round(skill_sc, 4),
            interaction_bonus = round(interaction, 4),
            years_match       = round(yoe_sc,   4),
            level_match       = round(level_sc, 4),
            education_match   = round(edu_sc,   4),
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
            matched_skills      = jd_match.matched_skills,
            missing_skills      = jd_match.missing_skills,
            pretty_salary       = row.pretty_salary,
        )))

    # 5. Filter >= 35% (lowered threshold for better recall), Sort descending and return top_n
    filtered_scored = [(s, r) for s, r in scored if s >= 0.35]
    filtered_scored.sort(key=lambda t: t[0], reverse=True)

    # If we have too few results, lower threshold further
    if len(filtered_scored) < top_n:
        remaining = [(s, r) for s, r in scored if 0.25 <= s < 0.35]
        remaining.sort(key=lambda t: t[0], reverse=True)
        filtered_scored.extend(remaining)

    return [r for _, r in filtered_scored[:top_n]]
