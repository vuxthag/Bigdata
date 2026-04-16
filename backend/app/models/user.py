"""
models/user.py
==============
SQLAlchemy ORM model for the users table.

Phase 1 additions:
  - role column with CHECK constraint (candidate | employer | admin)
  - company relationship (one employer → one company)
  - applications relationship (candidate applications)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('candidate', 'employer', 'admin')",
            name="ck_users_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── RBAC ──────────────────────────────────────────────────────────────────
    role: Mapped[str] = mapped_column(
        String(20), default="candidate", server_default="candidate", nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships — existing
    cvs: Mapped[list["CV"]] = relationship("CV", back_populates="user", cascade="all, delete-orphan")
    interactions: Mapped[list["UserInteraction"]] = relationship(
        "UserInteraction", back_populates="user", cascade="all, delete-orphan"
    )

    # Relationships — Phase 1
    company: Mapped["Company | None"] = relationship(
        "Company",
        back_populates="owner",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="Company.owner_id",
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application",
        back_populates="candidate",
        cascade="all, delete-orphan",
        foreign_keys="Application.candidate_id",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
