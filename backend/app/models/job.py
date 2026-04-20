"""
models/job.py
=============
SQLAlchemy ORM model for the job_descriptions table.
Simplified for candidate-only platform — all jobs are crawled from VietnamWorks.

Fields:
  - position_title : job title
  - description    : full job description
  - cleaned_description: preprocessed text for ML
  - embedding      : SBERT vector (384-dim)
  - company        : employer name string (from crawler)
  - location       : job location
  - link           : canonical URL (unique) — dedup key for crawler
  - skills         : ARRAY of extracted skill strings
  - salary_min/max : salary range
  - job_type       : full-time, part-time, remote, etc.
  - source         : crawler source (vietnamworks, seed, manual)
  - is_active      : soft delete flag
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean, DateTime, ForeignKey,
    Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base

if TYPE_CHECKING:
    from app.models.interaction import UserInteraction


class Job(Base):
    __tablename__ = "job_descriptions"
    __table_args__ = (
        UniqueConstraint("link", name="uq_job_link"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    position_title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="vietnamworks", nullable=False)
    external_job_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Crawler fields
    company: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    company_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    company_profile: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    link: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    pretty_salary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    years_of_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    job_level: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_function: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=func.now()
    )

    # Optional metadata
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    job_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Full-text search (populated by DB trigger)
    search_vector = mapped_column(TSVECTOR, nullable=True)

    # Relationships
    interactions: Mapped[list["UserInteraction"]] = relationship(
        "UserInteraction", back_populates="job"
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} title={self.position_title}>"
