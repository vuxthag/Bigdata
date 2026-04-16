"""
models/job.py
=============
SQLAlchemy ORM model for the job_descriptions table.

Crawler-added fields (nullable, backward-compatible):
  - company        : employer name string (legacy/crawler field)
  - location       : job location string
  - link           : canonical URL (unique) — dedup key for crawler
  - skills         : ARRAY of extracted skill strings
  - updated_at     : last time the crawler refreshed this record

Phase 1 additions (all nullable for backward compat):
  - company_id     : FK → companies.id (proper company ownership)
  - status         : draft | published | closed  (default: published)
  - salary_min     : INT, minimum salary
  - salary_max     : INT, maximum salary
  - job_type       : e.g. full-time, part-time, contract, remote
  - deadline       : DATE, application deadline
  - applicant_count: INT, denormalized counter (updated by trigger/app)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey,
    Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base


class Job(Base):
    __tablename__ = "job_descriptions"
    __table_args__ = (
        UniqueConstraint("link", name="uq_job_link"),
        CheckConstraint(
            "status IN ('draft', 'published', 'closed')",
            name="ck_job_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    position_title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Crawler fields (nullable — existing rows unaffected) ──────────────────
    company: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    link: Mapped[str | None] = mapped_column(Text, nullable=True)   # unique via __table_args__
    skills: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=func.now()
    )

    # ── Phase 1 fields (all nullable — backward-compatible) ───────────────────
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), default="published", server_default="published", nullable=False
    )
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    job_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    applicant_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

    # Relationships — existing
    interactions: Mapped[list["UserInteraction"]] = relationship(
        "UserInteraction", back_populates="job"
    )

    # Relationships — Phase 1
    company_rel: Mapped["Company | None"] = relationship(
        "Company", back_populates="jobs", foreign_keys=[company_id]
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} title={self.position_title} status={self.status}>"
