"""
services/auth_service.py
=========================
JWT authentication and password hashing utilities.

Bcrypt fixes:
- Pre-hash password with SHA-256 before bcrypt to avoid the 72-byte limit
- SHA-256 always produces a 32-byte digest (within bcrypt's limit)
- Compatible with bcrypt==4.0.1 + passlib==1.7.4
"""
from __future__ import annotations

import hashlib
import base64
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

# ── Password hashing ──────────────────────────────────────────────────────────
# Use bcrypt with explicit rounds; disable the __about__ compatibility check
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)

# ── Bearer token extractor ────────────────────────────────────────────────────
bearer_scheme = HTTPBearer()

# Max password length before rejecting at the API level
MAX_PASSWORD_LENGTH = 128


def _prehash_password(password: str) -> str:
    """
    SHA-256 pre-hash the password then base64-encode it.
    This produces a 44-char ASCII string — safely within bcrypt's 72-byte limit.
    The base64 encoding ensures no null bytes that bcrypt would truncate.
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("ascii")  # always 44 chars


def hash_password(password: str) -> str:
    """
    Securely hash a password.
    - Rejects passwords > 128 chars (raises ValueError, caller converts to 422)
    - Pre-hashes with SHA-256 to stay within bcrypt's 72-byte limit
    """
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password too long (max {MAX_PASSWORD_LENGTH} characters)")
    return pwd_context.hash(_prehash_password(password))


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    if len(plain) > MAX_PASSWORD_LENGTH:
        return False
    return pwd_context.verify(_prehash_password(plain), hashed)


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    """
    Create a signed JWT access token.

    Returns
    -------
    tuple[str, int]
        (token_string, expires_in_seconds)
    """
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    expire = datetime.now(tz=timezone.utc) + timedelta(seconds=expires_in)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(tz=timezone.utc),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> dict | None:
    """Decode and verify a JWT token. Returns payload or None if invalid."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    FastAPI dependency: extract and validate the current JWT user.
    Raises 401 if token is missing, invalid, or user not found.
    """
    from app.models.user import User

    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
