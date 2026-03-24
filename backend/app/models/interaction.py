"""
models/interaction.py
======================
SQLAlchemy ORM model for user_interactions table.
Used as training signal for continual learning.

Label mapping:
  'applied' / 'saved'  → positive pair (label = 1.0)
  'skipped'            → negative pair (label = 0.0)
  'viewed'             → neutral, not used for training
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InteractionAction(str, enum.Enum):
    viewed = "viewed"
    applied = "applied"
    saved = "saved"
    skipped = "skipped"


class UserInteraction(Base):
    __tablename__ = "user_interactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cv_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cvs.id", ondelete="SET NULL"), nullable=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[InteractionAction] = mapped_column(
        Enum(InteractionAction, name="interaction_action_enum"), nullable=False
    )
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_trained: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="interactions")
    cv: Mapped["CV"] = relationship("CV", back_populates="interactions")
    job: Mapped["Job"] = relationship("Job", back_populates="interactions")

    def __repr__(self) -> str:
        return f"<UserInteraction user={self.user_id} job={self.job_id} action={self.action}>"
