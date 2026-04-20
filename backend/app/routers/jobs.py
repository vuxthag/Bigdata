"""
routers/jobs.py
===============
Job descriptions: list, get, and create endpoints.

Search strategy (same approach as VietnamWorks / LinkedIn / Indeed):
  1. PostgreSQL full-text search (GIN index on tsvector) for fast keyword
     retrieval — handles short queries like "IT", "Python", "Marketing".
  2. SBERT semantic search via pgvector for conceptual matches when the
     query is longer (≥ 3 words) or when text search returns too few hits.
  3. Ranking: ts_rank (text relevance) + cosine similarity, with title
     matches boosted.
"""
from __future__ import annotations

import logging
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, literal, or_, select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.ml.preprocessing import clean_text
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobCreate, JobListResponse, JobResponse
from app.services.auth_service import get_current_user
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["Jobs"])

# Minimum text-search results before we also add semantic results
_SEMANTIC_FALLBACK_THRESHOLD = 20


def _build_tsquery(raw: str) -> str:
    """
    Convert user input into a PostgreSQL tsquery string.
    'IT developer Python' → 'IT:* & developer:* & Python:*'
    Each token gets prefix-matching (:*) so partial words work.
    """
    tokens = re.findall(r"[A-Za-z0-9\u00C0-\u024F#+.]+", raw)
    if not tokens:
        return ""
    return " & ".join(f"{t}:*" for t in tokens)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
):
    """
    Hybrid job search:
      - No query → latest jobs (created_at DESC).
      - With query → full-text search (GIN index) ranked by ts_rank,
        with semantic fallback for longer / conceptual queries.
    """
    base = Job.is_active.is_(True)
    search = search.strip()

    # ── No search: latest jobs ───────────────────────────────────
    if not search:
        count_q = select(func.count(Job.id)).where(base)
        total = (await db.execute(count_q)).scalar_one()

        q = (
            select(Job).where(base)
            .order_by(Job.created_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )
        jobs = (await db.execute(q)).scalars().all()

        return JobListResponse(
            items=[JobResponse.model_validate(j) for j in jobs],
            total=total, page=page, page_size=page_size,
        )

    # ── Phase 1: Full-text search (fast, GIN-indexed) ────────────
    tsq_str = _build_tsquery(search)
    like_pattern = f"%{search}%"

    if tsq_str:
        tsquery = func.to_tsquery("english", tsq_str)
        fts_filter = Job.search_vector.op("@@")(tsquery)
        fts_rank = func.ts_rank(Job.search_vector, tsquery)
    else:
        fts_filter = None
        fts_rank = literal(0)

    # Also match exact title substring (catches things FTS might miss,
    # e.g. "C++" or abbreviations). Uses the position_title index.
    title_like = Job.position_title.ilike(like_pattern)

    if fts_filter is not None:
        text_filter = or_(fts_filter, title_like)
    else:
        text_filter = title_like

    # Count text matches
    text_count_q = select(func.count(Job.id)).where(base, text_filter)
    text_total = (await db.execute(text_count_q)).scalar_one()

    # ── Phase 2: Decide if we need semantic expansion ────────────
    word_count = len(search.split())
    need_semantic = (
        text_total < _SEMANTIC_FALLBACK_THRESHOLD or word_count >= 3
    )

    if need_semantic:
        # Build search embedding (prefer a reference job's embedding)
        ref_result = await db.execute(
            select(Job.embedding).where(
                title_like, base, Job.embedding.isnot(None),
            ).limit(1)
        )
        ref_emb = ref_result.scalar_one_or_none()

        if ref_emb:
            emb_str = "[" + ",".join(str(x) for x in ref_emb) + "]"
        else:
            emb = embedding_service.encode(search)
            emb_str = "[" + ",".join(f"{x:.6f}" for x in emb.tolist()) + "]"

        cosine_dist = Job.embedding.op("<=>")(emb_str)
        sem_filter = cosine_dist <= 0.75  # similarity >= 0.25

        # Hybrid: text OR semantic
        hybrid = or_(text_filter, sem_filter)
        count_q = select(func.count(Job.id)).where(base, hybrid)
        total = (await db.execute(count_q)).scalar_one()

        # Rank: title match first, then FTS rank + semantic closeness
        title_boost = case(
            (title_like, literal(0)),
            else_=literal(1),
        )
        q = (
            select(Job).where(base, hybrid)
            .order_by(title_boost, fts_rank.desc(), cosine_dist)
            .offset((page - 1) * page_size).limit(page_size)
        )
    else:
        # Text-only (enough hits, fast path)
        total = text_total
        title_boost = case(
            (title_like, literal(0)),
            else_=literal(1),
        )
        q = (
            select(Job).where(base, text_filter)
            .order_by(title_boost, fts_rank.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )

    jobs = (await db.execute(q)).scalars().all()

    return JobListResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a single job by ID."""
    result = await db.execute(select(Job).where(Job.id == job_id, Job.is_active))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResponse.model_validate(job)


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    body: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new job description (requires authentication)."""
    cleaned = clean_text(body.description)
    embedding_vec = embedding_service.encode(cleaned)

    job = Job(
        position_title=body.position_title,
        description=body.description,
        cleaned_description=cleaned,
        embedding=embedding_vec.tolist(),
        source="user",
        created_by=current_user.id,
    )
    db.add(job)
    await db.flush()
    await db.commit()
    await db.refresh(job)
    return JobResponse.model_validate(job)


@router.post("/upload", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def upload_job(
    body: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a new job description (alias for POST /jobs)."""
    return await create_job(body, db, current_user)


@router.delete("/{job_id}", status_code=status.HTTP_200_OK)
async def delete_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a job (set is_active = False)."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    job.is_active = False
    await db.commit()
    return {"message": "Job deleted successfully"}


@router.post("/admin/regenerate-embeddings", status_code=status.HTTP_200_OK)
async def regenerate_embeddings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Admin endpoint: Regenerate embeddings for all jobs that don't have one.
    This is useful after seeding jobs from CSV without embeddings.
    """
    # Get all jobs without embeddings
    result = await db.execute(
        select(Job).where(
            Job.embedding.is_(None),
            Job.is_active.is_(True),
            Job.cleaned_description.isnot(None)
        )
    )
    jobs_without_embeddings = result.scalars().all()

    if not jobs_without_embeddings:
        return {"message": "No jobs without embeddings found", "processed": 0}

    total = len(jobs_without_embeddings)
    logger.info(f"[Admin] Found {total} jobs without embeddings")

    # Process in batches
    batch_size = 50
    processed = 0
    errors = 0

    for i in range(0, total, batch_size):
        batch = jobs_without_embeddings[i:i + batch_size]
        texts = [j.cleaned_description for j in batch if j.cleaned_description]

        if not texts:
            continue

        try:
            embeddings = embedding_service.encode_batch(texts, batch_size=len(texts))
            for j, emb in zip(batch, embeddings):
                j.embedding = emb.tolist()
                processed += 1

            await db.flush()
            logger.info(f"[Admin] Processed batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}")
        except Exception as e:
            logger.error(f"[Admin] Error processing batch: {e}")
            errors += len(batch)

    await db.commit()

    return {
        "message": f"Embeddings regenerated for {processed} jobs",
        "processed": processed,
        "errors": errors,
        "total_without_embeddings": total
    }
