"""
schemas/application_schema.py
==============================
Pydantic request/response schemas for the application flow.

Covers:
  - Candidate: submit application, list own applications
  - Employer:  list job applications, update application status
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Shared
# ─────────────────────────────────────────────────────────────────────────────

ApplicationStatusValue = Literal[
    "applied", "reviewed", "interview", "offered", "rejected", "hired"
]


# ─────────────────────────────────────────────────────────────────────────────
# Candidate — Apply
# ─────────────────────────────────────────────────────────────────────────────

class ApplyRequest(BaseModel):
    """Body for POST /candidate/applications."""
    job_id: uuid.UUID
    cv_id: uuid.UUID | None = Field(default=None)
    cover_letter: str | None = Field(default=None, max_length=5000)


class ApplyResponse(BaseModel):
    """Immediate response after successfully submitting an application."""
    message: str
    application_id: uuid.UUID


# ─────────────────────────────────────────────────────────────────────────────
# Candidate — My Applications
# ─────────────────────────────────────────────────────────────────────────────

class JobSummary(BaseModel):
    """Minimal job info embedded in a candidate's application list item."""
    id: uuid.UUID
    title: str
    company_name: str | None   # None if job has no linked company yet
    status: str                # job status: published / draft / closed

    model_config = {"from_attributes": True}


class CandidateApplicationItem(BaseModel):
    """One row in GET /candidate/applications."""
    application_id: uuid.UUID
    job: JobSummary
    status: ApplicationStatusValue
    applied_at: datetime
    cover_letter: str | None

    model_config = {"from_attributes": True}


class CandidateApplicationListResponse(BaseModel):
    items: list[CandidateApplicationItem]
    total: int


# ─────────────────────────────────────────────────────────────────────────────
# Employer — Applications for a Job
# ─────────────────────────────────────────────────────────────────────────────

class CandidateSummary(BaseModel):
    """Minimal candidate info embedded in an employer's applicant list."""
    id: uuid.UUID
    name: str | None
    email: str

    model_config = {"from_attributes": True}


class EmployerApplicationItem(BaseModel):
    """One row in GET /employer/applications/{job_id}."""
    application_id: uuid.UUID
    candidate: CandidateSummary
    cv_id: uuid.UUID | None
    status: ApplicationStatusValue
    applied_at: datetime
    cover_letter: str | None
    note: str | None
    match_score: float | None = None   # future: filled by ML recommendation

    model_config = {"from_attributes": True}


class EmployerApplicationListResponse(BaseModel):
    items: list[EmployerApplicationItem]
    total: int
    job_id: uuid.UUID


# ─────────────────────────────────────────────────────────────────────────────
# Employer — Update Application Status
# ─────────────────────────────────────────────────────────────────────────────

class UpdateStatusRequest(BaseModel):
    """Body for PATCH /employer/applications/{id}/status."""
    status: ApplicationStatusValue


class UpdateStatusResponse(BaseModel):
    message: str
    application_id: uuid.UUID
    new_status: ApplicationStatusValue
