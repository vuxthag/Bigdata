"""
schemas/job.py
==============
Pydantic schemas for job description endpoints.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    position_title: str = Field(max_length=255)
    description: str = Field(min_length=20)


class JobResponse(BaseModel):
    id: uuid.UUID
    position_title: str
    description: str
    created_at: datetime
    source: str

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
