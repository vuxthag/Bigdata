"""
models/cv.py
============
SQLAlchemy ORM model for the cvs table.
Stores uploaded CV text and its Sentence-BERT embedding (384-dim vector).

Phase 1 addition:
  - applications relationship (a CV can be referenced by many applications)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base

if TYPE_CHECKING:
    from app.models.interaction import UserInteraction
    from app.models.user import User


class CV(Base):
    __tablename__ = "cvs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    file_size_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships — existing
    user: Mapped["User"] = relationship("User", back_populates="cvs")
    interactions: Mapped[list["UserInteraction"]] = relationship(
        "UserInteraction", back_populates="cv"
    )



    def __repr__(self) -> str:
        return f"<CV id={self.id} filename={self.filename}>"
