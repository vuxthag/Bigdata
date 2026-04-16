"""
schemas/company_schema.py
==========================
Pydantic request/response schemas for employer company management.

Covers:
  - Create / Update company profile
  - Response shape returned to callers
  - Logo upload response
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Request schemas
# ─────────────────────────────────────────────────────────────────────────────

class CompanyCreate(BaseModel):
    """Body for POST /employer/company."""
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    industry: str | None = Field(default=None, max_length=100)
    size: str | None = Field(default=None, max_length=50,
                             description="e.g. '1-10', '11-50', '51-200', '201-500', '500+'")
    location: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=500)


class CompanyUpdate(BaseModel):
    """Body for PUT /employer/company/me  — all fields optional."""
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    industry: str | None = Field(default=None, max_length=100)
    size: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=500)


# ─────────────────────────────────────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────────────────────────────────────

class CompanyResponse(BaseModel):
    """Full company profile returned to the employer."""
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    slug: str | None
    description: str | None
    industry: str | None
    size: str | None
    location: str | None
    website: str | None
    logo_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompanyCreateResponse(BaseModel):
    """Slim response immediately after company creation."""
    id: uuid.UUID
    name: str
    slug: str | None
    message: str = "Company created successfully"

    model_config = {"from_attributes": True}


class LogoUploadResponse(BaseModel):
    """Response after uploading a company logo."""
    logo_url: str
    message: str = "Logo uploaded successfully"
