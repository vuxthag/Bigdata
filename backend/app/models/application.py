"""
models/application.py
=====================
SQLAlchemy ORM model for the applications table.

Replaces the misuse of user_interactions(action='applied').

Business rules enforced here:
  - One application per (job_id, candidate_id) pair — UNIQUE constraint
  - Deleting a job  → cascades and removes all its applications
  - Deleting a user → cascades and removes their applications
  - CV reference is optional (SET NULL on CV delete)

Allowed status values (enforced at app layer, documented here):
  applied | reviewed | interview | offered | rejected | hired
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base


class ApplicationStatus(str, enum.Enum):
    applied   = "applied"
    reviewed  = "reviewed"
    interview = "interview"
    offered   = "offered"
    rejected  = "rejected"
    hired     = "hired"


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        # Business rule: a candidate may apply to a job only once
        UniqueConstraint("job_id", "candidate_id", name="unique_application"),
        # Index for employer queries: "show me all applications for job X"
        Index("ix_applications_job_id", "job_id"),
        # Index for candidate queries: "show me all my applications"
        Index("ix_applications_candidate_id", "candidate_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    cv_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cvs.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(
            ApplicationStatus,
            name="application_status_enum",
            create_type=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ApplicationStatus.applied,
        nullable=False,
    )

    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Phase 4 — AI Ranking ──────────────────────────────────────────────────
    match_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Composite AI ranking score [0..1]"
    )

    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    job:       Mapped["Job"]  = relationship("Job",  back_populates="applications")
    candidate: Mapped["User"] = relationship("User", back_populates="applications", foreign_keys=[candidate_id])
    cv:        Mapped["CV"]   = relationship("CV",   back_populates="applications")

    def __repr__(self) -> str:
        return (
            f"<Application id={self.id} job={self.job_id} "
            f"candidate={self.candidate_id} status={self.status}>"
        )
