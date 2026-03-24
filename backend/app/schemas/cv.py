"""
schemas/cv.py
=============
Pydantic schemas for CV upload and list endpoints.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class CVResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_size_kb: int | None
    uploaded_at: datetime
    user_id: uuid.UUID

    model_config = {"from_attributes": True}


class CVListResponse(BaseModel):
    items: list[CVResponse]
    total: int
