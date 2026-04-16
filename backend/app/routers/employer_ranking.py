"""
routers/employer_ranking.py
============================
AI Ranking endpoints for the employer portal.

Routes
------
GET  /api/v1/employer/rank-candidates/{job_id}
     Return all applicants for a job, ranked by multi-signal AI score.
     Scores are persisted to applications.match_score asynchronously.

POST /api/v1/employer/feedback/{application_id}
     Apply a hiring decision feedback signal to adjust an applicant's score.
     Outcomes: hired | rejected | interview | offered

Auth: JWT required, role must be 'employer'.
The employer must OWN the job.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.ranking_schema import (
    FeedbackRequest,
    FeedbackResponse,
    RankCandidatesResponse,
)
from app.services.auth_service import get_current_user
from app.services.ranking_service import (
    apply_feedback_signal,
    rank_candidates_for_job,
    DEFAULT_WEIGHTS,
)

router = APIRouter(prefix="/employer", tags=["Employer — AI Ranking"])


# ── Guards ────────────────────────────────────────────────────────────────────

def _require_employer(current_user: User) -> User:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can access this endpoint",
        )
    return current_user


def _map_error(exc: ValueError) -> None:
    code = str(exc)
    mapping = {
        "job_not_found":          (status.HTTP_404_NOT_FOUND,  "Job not found"),
        "application_not_found":  (status.HTTP_404_NOT_FOUND,  "Application not found"),
        "forbidden":              (status.HTTP_403_FORBIDDEN,   "You do not own this resource"),
    }
    http_status, detail = mapping.get(code, (status.HTTP_500_INTERNAL_SERVER_ERROR, code))
    raise HTTPException(status_code=http_status, detail=detail)


# ── GET /employer/rank-candidates/{job_id} ────────────────────────────────────

@router.get(
    "/rank-candidates/{job_id}",
    response_model=RankCandidatesResponse,
    summary="AI-ranked list of applicants for a job",
)
async def rank_candidates(
    job_id: uuid.UUID,
    # Optional weight overrides
    w_cosine:      Annotated[float, Query(ge=0.0, le=1.0, description="Weight for cosine similarity")]     = DEFAULT_WEIGHTS["cosine"],
    w_skill:       Annotated[float, Query(ge=0.0, le=1.0, description="Weight for skill overlap")]         = DEFAULT_WEIGHTS["skill"],
    w_interaction: Annotated[float, Query(ge=0.0, le=1.0, description="Weight for interaction bonus")]    = DEFAULT_WEIGHTS["interaction"],
    w_yoe:         Annotated[float, Query(ge=0.0, le=1.0, description="Weight for years-of-experience")]  = DEFAULT_WEIGHTS["yoe"],
    db:            AsyncSession = Depends(get_db),
    current_user:  User        = Depends(get_current_user),
) -> RankCandidatesResponse:
    """
    Return all applicants for the given job, **ranked by AI match score** (descending).

    The composite score integrates:
    - **Cosine similarity** between CV embedding and job description embedding (SBERT)
    - **Skill overlap** — Jaccard similarity on extracted tech-skill sets
    - **Interaction bonus** — positive/negative signal from candidate browsing behaviour
    - **Years-of-experience compatibility** — regex-extracted from CV vs JD

    Weights can be overridden per-request via query params.

    Results are **cached** (TTL 5 min) and scores are **persisted** to
    `applications.match_score` asynchronously for display in the standard list endpoint.
    """
    _require_employer(current_user)

    weights = {
        "cosine":      w_cosine,
        "skill":       w_skill,
        "interaction": w_interaction,
        "yoe":         w_yoe,
    }

    try:
        result = await rank_candidates_for_job(
            job_id=job_id,
            employer_id=current_user.id,
            db=db,
            weights=weights,
        )
    except ValueError as exc:
        _map_error(exc)

    return result


# ── POST /employer/feedback/{application_id} ──────────────────────────────────

@router.post(
    "/feedback/{application_id}",
    response_model=FeedbackResponse,
    summary="Apply hiring-decision feedback to adjust AI score",
)
async def submit_feedback(
    application_id: uuid.UUID,
    body:           FeedbackRequest,
    db:             AsyncSession = Depends(get_db),
    current_user:   User        = Depends(get_current_user),
) -> FeedbackResponse:
    """
    Record a hiring decision outcome and update the applicant's AI match score.

    **Outcome → score delta:**
    | Outcome   | Δ score |
    |-----------|---------|
    | hired     | +0.08   |
    | offered   | +0.04   |
    | interview | +0.02   |
    | rejected  | -0.05   |

    - Clamps final score to **[0, 1]**
    - Invalidates the ranking cache for the job
    - **Does NOT** change the application status (use `PATCH /applications/{id}/status`)
    """
    _require_employer(current_user)

    try:
        new_score = await apply_feedback_signal(
            application_id=application_id,
            outcome=body.outcome,
            employer_id=current_user.id,
            db=db,
        )
    except ValueError as exc:
        _map_error(exc)

    return FeedbackResponse(
        message        = f"Feedback '{body.outcome}' applied successfully",
        application_id = application_id,
        outcome        = body.outcome,
        new_score      = new_score,
    )
