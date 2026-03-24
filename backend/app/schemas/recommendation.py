"""
schemas/recommendation.py
==========================
Pydantic schemas for recommendation and feedback endpoints.
"""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class RecommendByTitleRequest(BaseModel):
    job_title: str = Field(min_length=2, max_length=255)
    top_n: int = Field(default=5, ge=1, le=20)


class RecommendByCVRequest(BaseModel):
    cv_id: uuid.UUID
    top_n: int = Field(default=5, ge=1, le=20)


class RecommendedJob(BaseModel):
    job_id: uuid.UUID
    position_title: str
    description_preview: str   # first 200 chars
    similarity_score: float    # 0.0 – 1.0

    model_config = {"from_attributes": True}


class RecommendResponse(BaseModel):
    query: str
    results: list[RecommendedJob]
    model_version: str


class InteractionCreate(BaseModel):
    job_id: uuid.UUID
    action: Literal["viewed", "applied", "saved", "skipped"]
    cv_id: uuid.UUID | None = None
    similarity_score: float | None = None
