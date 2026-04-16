"""
schemas/ranking_schema.py
==========================
Pydantic schemas for the AI ranking endpoints.

New endpoints:
  GET  /api/v1/employer/rank-candidates/{job_id}
  POST /api/v1/employer/feedback/{application_id}
  GET  /api/v1/candidate/ranked-jobs   (improved recommendation)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.application_schema import CandidateSummary


# ── Score breakdown (transparent scoring) ─────────────────────────────────────

class ScoreBreakdown(BaseModel):
    """Decomposed ranking score components."""
    cosine_similarity: float = Field(ge=0.0, le=1.0, description="SBERT embedding similarity")
    skill_overlap:     float = Field(ge=0.0, le=1.0, description="Jaccard on extracted skill sets")
    interaction_bonus: float = Field(ge=0.0, le=1.0, description="Signal from candidate interactions")
    years_match:       float = Field(ge=0.0, le=1.0, description="YOE compatibility score")


# ── Employer → Candidate ranking ──────────────────────────────────────────────

class RankedCandidate(BaseModel):
    """One applicant row, enriched with AI ranking score."""
    application_id:  uuid.UUID
    candidate:       CandidateSummary
    cv_id:           uuid.UUID | None
    status:          str
    match_score:     float = Field(ge=0.0, le=1.0, description="Composite AI score")
    score_breakdown: ScoreBreakdown
    applied_at:      datetime
    cover_letter:    str | None
    extracted_skills: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class RankCandidatesResponse(BaseModel):
    """Response for GET /employer/rank-candidates/{job_id}."""
    job_id:    uuid.UUID
    job_title: str
    total:     int
    items:     list[RankedCandidate]
    weights:   dict[str, float]   # actual weights used for this ranking


# ── Candidate → Job ranking (improved recommend) ───────────────────────────────

class RankedJob(BaseModel):
    """One job result with multi-signal score breakdown."""
    job_id:              uuid.UUID
    position_title:      str
    description_preview: str
    final_score:         float = Field(ge=0.0, le=1.0)
    score_breakdown:     ScoreBreakdown
    company:             str | None = None
    location:            str | None = None
    skills:              list[str]  = Field(default_factory=list)
    status:              str        = "published"
    salary_min:          int | None = None
    salary_max:          int | None = None

    model_config = {"from_attributes": True}


class RankedJobsResponse(BaseModel):
    """Response for GET /candidate/ranked-jobs."""
    cv_id:   uuid.UUID
    total:   int
    items:   list[RankedJob]
    weights: dict[str, float]


# ── Feedback learning ──────────────────────────────────────────────────────────

FeedbackOutcome = Literal["hired", "rejected", "interview", "offered"]


class FeedbackRequest(BaseModel):
    """Body for POST /employer/feedback/{application_id}."""
    outcome: FeedbackOutcome


class FeedbackResponse(BaseModel):
    """Confirms the feedback was applied."""
    message:        str
    application_id: uuid.UUID
    outcome:        FeedbackOutcome
    new_score:      float | None = Field(
        default=None,
        description="Updated match_score after applying feedback signal"
    )
