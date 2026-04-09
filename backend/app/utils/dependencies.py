"""
utils/dependencies.py
======================
FastAPI dependency functions.
Re-exports get_current_user for clean architecture.
"""
from __future__ import annotations

from app.services.auth_service import get_current_user

__all__ = ["get_current_user"]
