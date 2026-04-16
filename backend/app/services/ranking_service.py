"""
services/ranking_service.py
============================
AI Ranking System — core service layer.

Exposes three public async functions:

  rank_candidates_for_job(job_id, employer_id, db, weights?)
      → list[RankedCandidate]  sorted by match_score DESC
      → also persists scores to applications.match_score asynchronously

  rank_jobs_for_candidate(cv_id, db, top_n, weights?)
      → list[RankedJob]  improved multi-signal recommendation

  apply_feedback_signal(application_id, outcome, employer_id, db)
      → adjusts match_score based on hiring decision

Score formula
─────────────
  final_score = w1·cosine_similarity
              + w2·skill_overlap
              + w3·interaction_bonus
              + w4·yoe_match          (clamped to [0, 1])

Default weights: w1=0.60, w2=0.20, w3=0.15, w4=0.05

Feedback learning
─────────────────
  hired    → score  += FEEDBACK_DELTA  (0.08)
  rejected → score  -= FEEDBACK_DELTA  (0.05)
  interview/offered → no score change (informational only)
  Result clamped to [0, 1] and written to applications.match_score.

Caching
───────
  In-memory TTL cache keyed by (job_id, weights_hash).
  Invalidated on new application or status change via invalidate_ranking_cache().
  TTL = 5 minutes.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

import numpy as np
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.feature_engine import (
    build_interaction_bonus,
    extract_skills,
    skill_overlap,
    years_of_experience,
)
from app.models.application import Application
from app.models.company import Company
from app.models.cv import CV
from app.models.interaction import UserInteraction
from app.models.job import Job
from app.models.user import User
from app.schemas.ranking_schema import (
    RankedCandidate,
    RankedJob,
    RankCandidatesResponse,
    ScoreBreakdown,
)
from app.schemas.application_schema import CandidateSummary

logger = logging.getLogger(__name__)

# ── Default scoring weights ───────────────────────────────────────────────────
DEFAULT_WEIGHTS: dict[str, float] = {
    "cosine":      0.60,
    "skill":       0.20,
    "interaction": 0.15,
    "yoe":         0.05,
}

# ── Feedback deltas ───────────────────────────────────────────────────────────
FEEDBACK_DELTAS: dict[str, float] = {
    "hired":     +0.08,
    "offered":   +0.04,
    "interview": +0.02,
    "rejected":  -0.05,
}

# ── In-memory TTL cache ───────────────────────────────────────────────────────
_CACHE_TTL_SECONDS = 300   # 5 minutes

@dataclass
class _CacheEntry:
    data: Any
    expires_at: float


_cache: dict[str, _CacheEntry] = {}


def _cache_key(job_id: uuid.UUID, weights: dict) -> str:
    w_str = str(sorted(weights.items()))
    return hashlib.md5(f"{job_id}:{w_str}".encode()).hexdigest()


def _cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry and time.monotonic() < entry.expires_at:
        return entry.data
    _cache.pop(key, None)
    return None


def _cache_set(key: str, data: Any) -> None:
    _cache[key] = _CacheEntry(data=data, expires_at=time.monotonic() + _CACHE_TTL_SECONDS)


def invalidate_ranking_cache(job_id: uuid.UUID | None = None) -> None:
    """
    Remove cached ranking results.
    If job_id is given, only invalidate entries for that job.
    Otherwise flush the entire cache.
    """
    if job_id is None:
        _cache.clear()
        return
    prefix = str(job_id)
    to_delete = [k for k in _cache if prefix in k]
    for k in to_delete:
        del _cache[k]


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
    # Linear interpolation: 0 at 0 years, 1 at jd_yoe years
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
        weights.get("cosine",      0.60) * cosine
        + weights.get("skill",     0.20) * skill
        + weights.get("interaction",0.15) * interaction
        + weights.get("yoe",       0.05) * yoe
    ) / total_w
    return float(np.clip(score, 0.0, 1.0))


# ── Ownership check (shared guard) ───────────────────────────────────────────

async def _verify_job_ownership(
    db: AsyncSession,
    job_id: uuid.UUID,
    employer_id: uuid.UUID,
) -> Job:
    """Raise ValueError if job not found or employer doesn't own it."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job: Job | None = result.scalar_one_or_none()
    if job is None:
        raise ValueError("job_not_found")

    if job.company_id is not None:
        comp_result = await db.execute(select(Company).where(Company.id == job.company_id))
        company: Company | None = comp_result.scalar_one_or_none()
        if company is None or company.owner_id != employer_id:
            raise ValueError("forbidden")
    else:
        if job.created_by != employer_id:
            raise ValueError("forbidden")

    return job


# ── Main public functions ─────────────────────────────────────────────────────

async def rank_candidates_for_job(
    job_id: uuid.UUID,
    employer_id: uuid.UUID,
    db: AsyncSession,
    weights: dict[str, float] | None = None,
) -> RankCandidatesResponse:
    """
    Rank all applicants for a job by multi-signal AI score.

    Steps:
    1. Verify employer owns the job.
    2. Fetch job embedding + skills.
    3. Fetch all applications + candidate CVs (batch).
    4. Compute composite score for each applicant.
    5. Sort descending by score.
    6. Fire-and-forget: persist scores to DB.

    Returns RankCandidatesResponse.
    """
    weights = weights or DEFAULT_WEIGHTS

    # Cache lookup
    cache_k = _cache_key(job_id, weights)
    cached = _cache_get(cache_k)
    if cached is not None:
        logger.debug(f"[Ranking] Cache hit for job {job_id}")
        return cached

    # 1. Ownership
    job = await _verify_job_ownership(db, job_id, employer_id)

    # 2. Job features
    jd_text   = (job.description or "") + " " + (job.position_title or "")
    jd_skills = extract_skills(jd_text)
    jd_yoe    = years_of_experience(jd_text)
    jd_emb    = np.array(job.embedding, dtype=np.float32) if job.embedding else None

    # 3. Fetch all applications for this job
    stmt = (
        select(Application, User, CV)
        .join(User, Application.candidate_id == User.id)
        .outerjoin(CV, Application.cv_id == CV.id)
        .where(Application.job_id == job_id)
        .order_by(Application.applied_at.desc())
    )
    rows = (await db.execute(stmt)).all()

    if not rows:
        response = RankCandidatesResponse(
            job_id=job_id,
            job_title=job.position_title,
            total=0,
            items=[],
            weights=weights,
        )
        _cache_set(cache_k, response)
        return response

    # 4. Score each applicant
    ranked: list[tuple[float, RankedCandidate]] = []

    for app, candidate, cv in rows:
        # -- Cosine similarity --
        if jd_emb is not None and cv is not None and cv.embedding is not None:
            cv_emb = np.array(cv.embedding, dtype=np.float32)
            cosine = _cosine(cv_emb, jd_emb)
        else:
            cosine = 0.0   # No embedding available

        # -- Skill overlap --
        cv_text   = (cv.raw_text or "") if cv else ""
        cv_skills = extract_skills(cv_text)
        skill_sc  = skill_overlap(cv_skills, jd_skills)

        # -- Interaction bonus --
        # Fetch interactions for this candidate (lightweight SELECT)
        int_result = await db.execute(
            select(UserInteraction.job_id, UserInteraction.action)
            .where(UserInteraction.user_id == candidate.id)
        )
        interactions = [
            {"job_id": str(r.job_id), "action": str(r.action)}
            for r in int_result.all()
        ]
        interaction_sc = build_interaction_bonus(interactions, str(job_id))

        # -- Years of experience compatibility --
        cv_yoe  = years_of_experience(cv_text)
        yoe_sc  = _yoe_compatibility(cv_yoe, jd_yoe)

        # -- Composite --
        final = _composite_score(cosine, skill_sc, interaction_sc, yoe_sc, weights)

        breakdown = ScoreBreakdown(
            cosine_similarity = round(cosine,        4),
            skill_overlap     = round(skill_sc,      4),
            interaction_bonus = round(interaction_sc, 4),
            years_match       = round(yoe_sc,         4),
        )

        status_val = app.status.value if hasattr(app.status, "value") else str(app.status)

        ranked.append((final, RankedCandidate(
            application_id   = app.id,
            candidate        = CandidateSummary(
                id    = candidate.id,
                name  = candidate.full_name,
                email = candidate.email,
            ),
            cv_id            = app.cv_id,
            status           = status_val,
            match_score      = round(final, 4),
            score_breakdown  = breakdown,
            applied_at       = app.applied_at,
            cover_letter     = app.cover_letter,
            extracted_skills = sorted(cv_skills),
        )))

    # Sort descending
    ranked.sort(key=lambda t: t[0], reverse=True)
    items = [r for _, r in ranked]

    response = RankCandidatesResponse(
        job_id    = job_id,
        job_title = job.position_title,
        total     = len(items),
        items     = items,
        weights   = weights,
    )

    # 5. Cache result
    _cache_set(cache_k, response)

    # 6. Persist scores to DB (background — don't await to keep response fast)
    asyncio.create_task(_persist_scores(job_id, items, db))

    return response


async def _persist_scores(
    job_id: uuid.UUID,
    items: list[RankedCandidate],
    db: AsyncSession,
) -> None:
    """Write match_score back to the applications table (fire-and-forget)."""
    try:
        for item in items:
            await db.execute(
                update(Application)
                .where(Application.id == item.application_id)
                .values(match_score=item.match_score)
            )
        await db.commit()
        logger.debug(f"[Ranking] Persisted {len(items)} scores for job {job_id}")
    except Exception as exc:
        logger.error(f"[Ranking] Failed to persist scores: {exc}")


async def rank_jobs_for_candidate(
    cv_id: uuid.UUID,
    db: AsyncSession,
    top_n: int = 10,
    weights: dict[str, float] | None = None,
) -> list[RankedJob]:
    """
    Improved job recommendation for a candidate using multi-signal scoring.

    Replaces pure cosine-similarity with:
      final_score = w1·cosine + w2·skill_overlap + w3·interaction + w4·yoe
    """
    weights = weights or DEFAULT_WEIGHTS

    # Fetch CV
    cv_result = await db.execute(select(CV).where(CV.id == cv_id))
    cv: CV | None = cv_result.scalar_one_or_none()
    if cv is None or cv.embedding is None:
        logger.warning(f"[Ranking] CV {cv_id} not found or has no embedding")
        return []

    cv_emb    = np.array(cv.embedding, dtype=np.float32)
    cv_text   = cv.raw_text or ""
    cv_skills = extract_skills(cv_text)
    cv_yoe    = years_of_experience(cv_text)

    # Fetch candidate interactions
    int_result = await db.execute(
        select(UserInteraction.job_id, UserInteraction.action)
        .where(UserInteraction.user_id == cv.user_id)
    )
    interactions = [
        {"job_id": str(r.job_id), "action": str(r.action)}
        for r in int_result.all()
    ]

    # Fetch published jobs with embeddings (top 200 candidates via pgvector pre-filter)
    from sqlalchemy import text as sa_text
    emb_str = _vec_to_str(cv.embedding)
    pre_filter_stmt = sa_text(
        """
        SELECT id, position_title, description, embedding,
               company, location, skills, status, salary_min, salary_max
        FROM job_descriptions
        WHERE is_active = true
          AND status    = 'published'
          AND embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT 200
        """
    )
    jd_rows = (await db.execute(pre_filter_stmt, {"emb": emb_str})).all()

    scored: list[tuple[float, RankedJob]] = []

    for row in jd_rows:
        jd_emb    = np.array(row.embedding, dtype=np.float32)
        jd_text   = (row.description or "") + " " + (row.position_title or "")
        jd_skills = extract_skills(jd_text)
        jd_yoe    = years_of_experience(jd_text)

        cosine       = _cosine(cv_emb, jd_emb)
        skill_sc     = skill_overlap(cv_skills, jd_skills)
        interaction  = build_interaction_bonus(interactions, str(row.id))
        yoe_sc       = _yoe_compatibility(cv_yoe, jd_yoe)
        final        = _composite_score(cosine, skill_sc, interaction, yoe_sc, weights)

        breakdown = ScoreBreakdown(
            cosine_similarity = round(cosine,       4),
            skill_overlap     = round(skill_sc,     4),
            interaction_bonus = round(interaction,  4),
            years_match       = round(yoe_sc,       4),
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
            status              = row.status,
            salary_min          = row.salary_min,
            salary_max          = row.salary_max,
        )))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [r for _, r in scored[:top_n]]


async def apply_feedback_signal(
    application_id: uuid.UUID,
    outcome: str,
    employer_id: uuid.UUID,
    db: AsyncSession,
) -> float:
    """
    Adjust an application's match_score based on employer hiring decision.

    Feedback deltas:
      hired     → +0.08
      offered   → +0.04
      interview → +0.02
      rejected  → -0.05

    Returns the updated match_score (clamped to [0, 1]).
    Raises ValueError on ownership errors.
    """
    # Load application
    app_result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    app: Application | None = app_result.scalar_one_or_none()
    if app is None:
        raise ValueError("application_not_found")

    # Ownership check
    await _verify_job_ownership(db, app.job_id, employer_id)

    delta     = FEEDBACK_DELTAS.get(outcome, 0.0)
    current   = float(app.match_score or 0.5)   # default neutral if not yet scored
    new_score = float(np.clip(current + delta, 0.0, 1.0))

    await db.execute(
        update(Application)
        .where(Application.id == application_id)
        .values(match_score=new_score)
    )
    await db.commit()

    # Invalidate cache for this job
    invalidate_ranking_cache(app.job_id)

    logger.info(
        f"[Ranking] Feedback applied: app={application_id} outcome={outcome} "
        f"score {current:.4f} → {new_score:.4f}"
    )
    return new_score
