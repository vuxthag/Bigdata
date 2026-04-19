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
    external_job_id: str | None = None

    company: str | None = None
    company_id: str | None = None
    company_profile: str | None = None

    location: str | None = None
    address: str | None = None
    link: str | None = None
    skills: list[str] | None = None

    pretty_salary: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None

    years_of_experience: int | None = None
    job_level: str | None = None
    industry: str | None = None
    job_function: str | None = None
    job_requirement: str | None = None
    benefits: str | None = None
    approved_on: datetime | None = None
    expired_on: datetime | None = None

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
