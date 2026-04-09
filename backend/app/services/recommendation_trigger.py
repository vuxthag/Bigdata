"""
app/services/recommendation_trigger.py
========================================
Real-time job-to-CV matching triggered when a new job is inserted.

Flow:
  1. Load the new job's embedding from DB
  2. Load all CV embeddings for all users
  3. Compute cosine similarity between job and each CV
  4. For top matches (score >= threshold), save a UserInteraction record
     with action="viewed" and the similarity score

This runs inside the crawler pipeline (after insert), so it's completely
automatic — no user action needed to see new jobs in recommendations.

Performance notes:
  - Skips CVs with no embedding
  - Caps at TOP_K_MATCHES CVs per job to avoid flooding the interactions table
  - Uses numpy for batch cosine similarity (fast even for 1000s of CVs)
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Config constants — can be moved to env vars later
SIMILARITY_THRESHOLD = 0.40   # minimum cosine similarity to save interaction
TOP_K_MATCHES = 10            # max CVs to match per job
MIN_EMBEDDING_NORM = 1e-8     # guard against zero vectors


async def trigger_recommendations_for_new_job(
    job_id: uuid.UUID,
    session: AsyncSession,
) -> int:
    """
    Compute job↔CV similarity for all users and save top matches.

    Args:
        job_id:  UUID of the newly inserted job
        session: Active async SQLAlchemy session

    Returns:
        Number of interaction records saved (0 if job has no embedding or no CVs)
    """
    import numpy as np
    from app.models.cv import CV
    from app.models.interaction import InteractionAction, UserInteraction
    from app.models.job import Job

    # ── 1. Load job embedding ──────────────────────────────────────────────
    job_result = await session.execute(
        select(Job.id, Job.embedding).where(Job.id == job_id)
    )
    job_row = job_result.first()

    if job_row is None or job_row.embedding is None:
        logger.debug(f"[RecTrigger] Job {job_id} has no embedding — skipping")
        return 0

    job_emb = np.array(job_row.embedding, dtype=np.float32)
    job_norm = np.linalg.norm(job_emb)
    if job_norm < MIN_EMBEDDING_NORM:
        logger.debug(f"[RecTrigger] Job {job_id} has zero embedding — skipping")
        return 0
    job_emb_normalized = job_emb / job_norm

    # ── 2. Load all CV embeddings ──────────────────────────────────────────
    cv_result = await session.execute(
        select(CV.id, CV.user_id, CV.embedding).where(CV.embedding.isnot(None))
    )
    cv_rows = cv_result.fetchall()

    if not cv_rows:
        logger.debug("[RecTrigger] No CVs with embeddings in DB — skipping")
        return 0

    # ── 3. Batch cosine similarity ─────────────────────────────────────────
    cv_ids = []
    user_ids = []
    cv_matrix = []

    for row in cv_rows:
        emb = np.array(row.embedding, dtype=np.float32)
        norm = np.linalg.norm(emb)
        if norm < MIN_EMBEDDING_NORM:
            continue
        cv_ids.append(row.id)
        user_ids.append(row.user_id)
        cv_matrix.append(emb / norm)

    if not cv_matrix:
        return 0

    cv_matrix_np = np.stack(cv_matrix, axis=0)   # shape: (N, D)
    similarities = cv_matrix_np @ job_emb_normalized  # cosine sim for each CV

    # ── 4. Filter top matches above threshold ─────────────────────────────
    # Get indices sorted by similarity descending
    ranked_indices = similarities.argsort()[::-1]

    saved = 0
    for idx in ranked_indices[:TOP_K_MATCHES]:
        score = float(similarities[idx])
        if score < SIMILARITY_THRESHOLD:
            break  # sorted desc, rest will also be below threshold

        cv_id = cv_ids[idx]
        user_id = user_ids[idx]

        # Avoid duplicate interactions: check if already exists for this user+job
        existing = await session.execute(
            select(UserInteraction.id).where(
                UserInteraction.user_id == user_id,
                UserInteraction.job_id == job_id,
            ).limit(1)
        )
        if existing.first() is not None:
            continue  # already matched

        interaction = UserInteraction(
            user_id=user_id,
            cv_id=cv_id,
            job_id=job_id,
            action=InteractionAction.viewed,
            similarity_score=round(score, 4),
            is_trained=False,
        )
        session.add(interaction)
        saved += 1

    if saved:
        logger.info(
            f"[RecTrigger] Job {job_id}: saved {saved} recommendation(s) "
            f"(threshold={SIMILARITY_THRESHOLD}, top_k={TOP_K_MATCHES})"
        )
    else:
        logger.debug(f"[RecTrigger] Job {job_id}: no matches above threshold {SIMILARITY_THRESHOLD}")

    return saved
