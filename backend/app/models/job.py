"""
models/job.py
=============
SQLAlchemy ORM model for the job_descriptions table.

Crawler-added fields (nullable, backward-compatible):
  - company        : employer name from job source
  - location       : job location string
  - link           : canonical URL (unique) — dedup key for crawler
  - skills         : ARRAY of extracted skill strings
  - updated_at     : last time the crawler refreshed this record
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


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

    # ── Crawler fields (nullable — existing rows unaffected) ──────────────
    company: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    link: Mapped[str | None] = mapped_column(Text, nullable=True)   # unique via __table_args__
    skills: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=func.now()
    )

    # Relationships
    interactions: Mapped[list["UserInteraction"]] = relationship(
        "UserInteraction", back_populates="job"
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} title={self.position_title}>"
