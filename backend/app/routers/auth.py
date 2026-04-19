"""
routers/auth.py
===============
Authentication endpoints: register, login, logout, me, google.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.user import RegisterResponse, TokenResponse, UserCreate, UserLogin, UserResponse
from app.services.auth_service import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user and return JWT token."""
    # Check duplicate email
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    try:
        hashed = hash_password(body.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    user = User(
        email=body.email,
        hashed_password=hashed,
        full_name=body.full_name,
    )
    db.add(user)
    await db.flush()  # get the UUID
    await db.commit()  # persist user to database immediately
    await db.refresh(user)  # reload server-generated fields

    token, expires_in = create_access_token(user.id)
    return RegisterResponse(
        user=UserResponse.model_validate(user),
        token=TokenResponse(access_token=token, expires_in=expires_in),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login with email/password and receive JWT token."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Client-side logout (clear token on frontend). Server acknowledges."""
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return UserResponse.model_validate(current_user)


# ── Google OAuth ─────────────────────────────────────────────────────────────

class GoogleTokenBody(BaseModel):
    credential: str  # Google ID token from frontend


@router.post("/google", response_model=TokenResponse)
async def google_login(body: GoogleTokenBody, db: AsyncSession = Depends(get_db)):
    """
    Verify Google ID token, create or find user, and return JWT.

    Flow:
    1. Frontend gets credential from Google Identity Services
    2. Backend verifies it with Google's tokeninfo endpoint
    3. Upsert user (match by google_id or email)
    4. Return app JWT
    """
    import httpx

    # Verify token with Google
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": body.credential},
        )
    if resp.status_code != 200:
        logger.warning("[Google Auth] Token verification failed: %s", resp.text)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")

    payload = resp.json()

    # Validate audience matches our client ID
    if settings.GOOGLE_CLIENT_ID and payload.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token audience mismatch")

    google_id = payload.get("sub")
    email = payload.get("email")
    name = payload.get("name")
    picture = payload.get("picture")

    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google account has no email")

    # Look up user by google_id first, then by email
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        # Try finding by email (user registered with email/password before)
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            # Link Google to existing account
            user.google_id = google_id
            if not user.avatar_url:
                user.avatar_url = picture
            if not user.full_name and name:
                user.full_name = name
        else:
            # Create new user
            user = User(
                email=email,
                full_name=name,
                google_id=google_id,
                avatar_url=picture,
                hashed_password=None,
            )
            db.add(user)

    await db.flush()
    await db.commit()
    await db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in)
