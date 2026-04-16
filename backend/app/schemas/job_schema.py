"""
schemas/job_schema.py
======================
Pydantic request/response schemas for employer job management (Phase 3).

Separate from the public-facing schemas/job.py to keep employer and
candidate surfaces cleanly decoupled.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field
from typing import Literal


# ─────────────────────────────────────────────────────────────────────────────
# Shared
# ─────────────────────────────────────────────────────────────────────────────

JobStatus = Literal["draft", "published", "closed"]


# ─────────────────────────────────────────────────────────────────────────────
# Request schemas
# ─────────────────────────────────────────────────────────────────────────────

class EmployerJobCreate(BaseModel):
    """Body for POST /employer/jobs — creates a draft job."""
    position_title: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=20, description="Full job description (HTML or plain text)")
    location: str | None = Field(default=None, max_length=255)
    job_type: str | None = Field(
        default=None, max_length=50,
        description="e.g. full-time, part-time, contract, remote"
    )
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    deadline: date | None = Field(default=None)
    skills: list[str] | None = Field(default=None, description="List of required skill tags")

    model_config = {
        "json_schema_extra": {
            "example": {
                "position_title": "Senior Python Developer",
                "description": "We are looking for an experienced Python developer...",
                "location": "Ha Noi, Vietnam",
                "job_type": "full-time",
                "salary_min": 2000,
                "salary_max": 4000,
                "deadline": "2026-06-30",
                "skills": ["Python", "FastAPI", "PostgreSQL"],
            }
        }
    }


class EmployerJobUpdate(BaseModel):
    """Body for PUT /employer/jobs/{id} — all fields optional."""
    position_title: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, min_length=20)
    location: str | None = Field(default=None, max_length=255)
    job_type: str | None = Field(default=None, max_length=50)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    deadline: date | None = Field(default=None)
    skills: list[str] | None = Field(default=None)


# ─────────────────────────────────────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class EmployerCompanyBrief(BaseModel):
    """Minimal company info embedded in job responses."""
    id: uuid.UUID
    name: str
    slug: str | None

    model_config = {"from_attributes": True}


class EmployerJobResponse(BaseModel):
    """Full job detail returned to the employer."""
    id: uuid.UUID
    position_title: str
    description: str
    location: str | None
    job_type: str | None
    salary_min: int | None
    salary_max: int | None
    deadline: date | None
    skills: list[str] | None
    status: str
    applicant_count: int
    company: EmployerCompanyBrief | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class EmployerJobCreateResponse(BaseModel):
    """Slim response immediately after job creation."""
    job_id: uuid.UUID
    status: str
    message: str = "Job created as draft"


class EmployerJobListResponse(BaseModel):
    """Paginated list of employer's own jobs."""
    items: list[EmployerJobResponse]
    total: int
    page: int
    page_size: int
    status_filter: str | None


class JobStatusUpdateResponse(BaseModel):
    """Response for publish / close actions."""
    job_id: uuid.UUID
    status: str
    message: str
