"""
schemas/ranking_schema.py
==========================
Pydantic schemas for the AI ranking endpoint (Candidate-Only).

Endpoint:
  GET /api/v1/recommend/ranked-jobs  — CV → ranked job list with scores
  POST /api/v1/recommend/cv-analysis — CV → full analysis with improvement tips
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
    level_match:       float = Field(ge=0.0, le=1.0, default=0.5, description="Job level compatibility")
    education_match:   float = Field(ge=0.0, le=1.0, default=0.5, description="Education compatibility")


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
    matched_skills:      list[str]     = Field(default_factory=list)
    missing_skills:      list[str]     = Field(default_factory=list)
    pretty_salary:       Optional[str] = None

    model_config = {"from_attributes": True}


class RankedJobsResponse(BaseModel):
    """Response for GET /recommend/ranked-jobs."""
    cv_id:   uuid.UUID
    total:   int
    items:   list[RankedJob]
    weights: dict[str, float]


# ── CV Analysis response ─────────────────────────────────────────────────────

class CVProfileResponse(BaseModel):
    """Structured CV profile extracted by AI."""
    skills:               list[str] = Field(default_factory=list)
    education_level:      Optional[str] = None
    years_of_experience:  float = 0.0
    detected_level:       Optional[str] = None


class CVAnalysisResponse(BaseModel):
    """Full CV analysis with job matches and improvement tips."""
    cv_id:              uuid.UUID
    cv_profile:         CVProfileResponse
    job_matches:        list[RankedJob]
    improvement_tips:   list[str] = Field(default_factory=list)
    top_missing_skills: list[str] = Field(default_factory=list)
