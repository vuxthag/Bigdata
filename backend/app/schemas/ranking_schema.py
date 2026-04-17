"""
schemas/ranking_schema.py
==========================
Pydantic schemas for the AI ranking endpoint (Candidate-Only).

Endpoint:
  GET /api/v1/recommend/ranked-jobs  — CV → ranked job list with scores
"""
from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, Field


# ── Score breakdown (transparent scoring) ─────────────────────────────────────

class ScoreBreakdown(BaseModel):
    """Decomposed ranking score components."""
    cosine_similarity: float = Field(ge=0.0, le=1.0, description="SBERT embedding similarity")
    skill_overlap:     float = Field(ge=0.0, le=1.0, description="Jaccard on extracted skill sets")
    interaction_bonus: float = Field(ge=0.0, le=1.0, description="Signal from candidate interactions")
    years_match:       float = Field(ge=0.0, le=1.0, description="YOE compatibility score")


# ── Candidate → Job ranking ────────────────────────────────────────────────────

class RankedJob(BaseModel):
    """One job result with multi-signal score breakdown."""
    job_id:              uuid.UUID
    position_title:      str
    description_preview: str
    final_score:         float = Field(ge=0.0, le=1.0)
    score_breakdown:     ScoreBreakdown
    company:             Optional[str] = None
    location:            Optional[str] = None
    skills:              list[str]     = Field(default_factory=list)
    salary_min:          Optional[int] = None
    salary_max:          Optional[int] = None

    model_config = {"from_attributes": True}


class RankedJobsResponse(BaseModel):
    """Response for GET /recommend/ranked-jobs."""
    cv_id:   uuid.UUID
    total:   int
    items:   list[RankedJob]
    weights: dict[str, float]
