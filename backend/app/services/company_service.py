"""
services/company_service.py
============================
Business logic for employer company management.

Responsibilities:
  - create_company()       — create once per employer, auto-slugify name
  - get_my_company()       — fetch employer's company (or None)
  - update_company()       — update mutable fields
  - update_logo_url()      — set logo_url after upload

All functions accept an AsyncSession — no session creation here.
"""
from __future__ import annotations

import re
import uuid
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Slug utility
# ─────────────────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    """
    Convert a company name to a URL-safe slug.
    Example: "Acme Corp & Partners!" → "acme-corp-partners"
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)          # remove non-word chars
    text = re.sub(r"[\s_]+", "-", text)            # whitespace/underscore → dash
    text = re.sub(r"-{2,}", "-", text)             # collapse consecutive dashes
    return text.strip("-")


async def _unique_slug(db: AsyncSession, base_slug: str) -> str:
    """
    Ensure the slug is unique in the companies table.
    If a conflict exists, appends a short UUID suffix.
    """
    result = await db.execute(select(Company).where(Company.slug == base_slug))
    if result.scalar_one_or_none() is None:
        return base_slug
    # Append 6-char UUID fragment for uniqueness
    suffix = uuid.uuid4().hex[:6]
    return f"{base_slug}-{suffix}"


# ─────────────────────────────────────────────────────────────────────────────
# CRUD operations
# ─────────────────────────────────────────────────────────────────────────────

async def create_company(
    db: AsyncSession,
    *,
    owner_id: uuid.UUID,
    name: str,
    description: str | None = None,
    industry: str | None = None,
    size: str | None = None,
    location: str | None = None,
    website: str | None = None,
) -> Company:
    """
    Create a new company for an employer.

    Raises
    ------
    ValueError("already_has_company")  → caller maps to 409
    """
    # Rule: one employer → one company
    existing = await db.execute(
        select(Company).where(Company.owner_id == owner_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError("already_has_company")

    slug = await _unique_slug(db, _slugify(name))

    company = Company(
        owner_id=owner_id,
        name=name,
        slug=slug,
        description=description,
        industry=industry,
        size=size,
        location=location,
        website=website,
    )
    db.add(company)
    await db.flush()
    await db.commit()
    await db.refresh(company)
    logger.info(f"[company] Created company {company.id} for owner {owner_id}")
    return company


async def get_my_company(
    db: AsyncSession,
    *,
    owner_id: uuid.UUID,
) -> Company | None:
    """
    Return the company owned by the employer, or None if they have none yet.
    """
    result = await db.execute(
        select(Company).where(Company.owner_id == owner_id)
    )
    return result.scalar_one_or_none()


async def update_company(
    db: AsyncSession,
    *,
    owner_id: uuid.UUID,
    name: str | None = None,
    description: str | None = None,
    industry: str | None = None,
    size: str | None = None,
    location: str | None = None,
    website: str | None = None,
) -> Company:
    """
    Update mutable fields of the employer's company.

    Raises
    ------
    ValueError("company_not_found")  → caller maps to 404
    """
    result = await db.execute(
        select(Company).where(Company.owner_id == owner_id)
    )
    company: Company | None = result.scalar_one_or_none()
    if company is None:
        raise ValueError("company_not_found")

    if name is not None:
        company.name = name
        # Re-slug when name changes, but keep suffix if needed
        company.slug = await _unique_slug(db, _slugify(name))
    if description is not None:
        company.description = description
    if industry is not None:
        company.industry = industry
    if size is not None:
        company.size = size
    if location is not None:
        company.location = location
    if website is not None:
        company.website = website

    await db.commit()
    await db.refresh(company)
    return company


async def update_logo_url(
    db: AsyncSession,
    *,
    owner_id: uuid.UUID,
    logo_url: str,
) -> Company:
    """
    Persist a new logo URL on the employer's company.

    Raises
    ------
    ValueError("company_not_found")  → caller maps to 404
    """
    result = await db.execute(
        select(Company).where(Company.owner_id == owner_id)
    )
    company: Company | None = result.scalar_one_or_none()
    if company is None:
        raise ValueError("company_not_found")

    company.logo_url = logo_url
    await db.commit()
    await db.refresh(company)
    return company
