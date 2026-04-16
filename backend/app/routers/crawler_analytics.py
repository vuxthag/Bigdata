"""
routers/crawler_analytics.py
==================================
Crawler monitoring analytics endpoints (Admin).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.crawl_log import CrawlLog
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/crawler/analytics", tags=["Crawler — Analytics"])

def _require_admin(current_user: User) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint"
        )
    return current_user

@router.get("", summary="Get crawler monitoring statistics")
async def get_crawler_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    # 1. Jobs crawled per source
    source_stats_res = await db.execute(
        select(
            CrawlLog.source,
            func.sum(CrawlLog.jobs_fetched).label("total_fetched"),
            func.sum(CrawlLog.jobs_inserted).label("total_inserted"),
            func.sum(CrawlLog.errors).label("total_errors"),
            func.sum(CrawlLog.jobs_skipped).label("total_skipped")
        )
        .group_by(CrawlLog.source)
    )
    
    source_stats = []
    global_fetched = 0
    global_errors = 0

    for row in source_stats_res.fetchall():
        source_stats.append({
            "source": row.source,
            "fetched": row.total_fetched or 0,
            "inserted": row.total_inserted or 0,
            "errors": row.total_errors or 0,
            "skipped": row.total_skipped or 0
        })
        global_fetched += (row.total_fetched or 0)
        global_errors += (row.total_errors or 0)

    # 2. Global error rate
    error_rate = 0.0
    if global_fetched > 0:
        error_rate = round((global_errors / global_fetched) * 100, 2)

    # 3. Block detection
    # If a recent run has 0 inserted and mostly errors, highly likely blocked.
    latest_logs_res = await db.execute(
        select(CrawlLog).order_by(CrawlLog.started_at.desc()).limit(5)
    )
    
    block_detection = False
    block_details = []

    for log in latest_logs_res.scalars().all():
        # High error threshold or 0 inserted but high fetched
        if log.errors > 0 and log.jobs_inserted == 0 and log.jobs_fetched > 0:
            block_detection = True
            block_details.append(f"Source {log.source}: {log.errors} errors, 0 insterted recently.")
        
        # Check specific error details for "403" or "block"
        if log.error_detail and ("403" in log.error_detail or "block" in log.error_detail.lower()):
            block_detection = True
            block_details.append(f"Source {log.source}: Encountered possible block ({log.error_detail[:50]}).")

    return {
        "jobs_per_source": source_stats,
        "error_rate": error_rate,
        "is_blocked": block_detection,
        "block_warnings": block_details
    }
