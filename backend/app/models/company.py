"""
models/company.py
=================
SQLAlchemy ORM model for the companies table.

Business rules:
  - Each employer owns ONE company (owner_id → users.id, UNIQUE)
  - Deleting a user cascades to their company
  - company.slug must be globally unique (used for public URLs)
  - owner_id must be a user with role='employer' (enforced at app layer)

Phase 1 of the Job Platform data foundation.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        # One employer → one company
        UniqueConstraint("owner_id", name="uq_company_owner"),
        UniqueConstraint("slug",     name="uq_company_slug"),
        Index("ix_companies_owner_id", "owner_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", name="fk_company_owner"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="company",
        foreign_keys=[owner_id],
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="company_rel",
        foreign_keys="Job.company_id",
    )

    def __repr__(self) -> str:
        return f"<Company id={self.id} name={self.name} owner={self.owner_id}>"
