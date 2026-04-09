"""
routers/crawler.py
==================
Crawler monitoring endpoints — stats and logs for the dashboard.

GET /api/v1/crawler/stats
    Returns summary statistics per source: jobs crawled today, errors, last run.

GET /api/v1/crawler/logs
    Returns the 50 most recent CrawlLog entries (all sources).

GET /api/v1/crawler/logs/{source}
    Returns the 50 most recent CrawlLog entries for a specific source.

These endpoints are open (no auth required) for easy monitoring dashboards,
internal tooling, and health checks. Add authentication if exposed publicly.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.crawl_log import CrawlLog

router = APIRouter(prefix="/crawler", tags=["Crawler Monitoring"])

KNOWN_SOURCES = ["itviec", "topcv", "vietnamworks"]


@router.get("/stats", summary="Crawler stats per source")
async def get_crawler_stats(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Return per-source crawler statistics for today and overall.

    Response shape:
    {
      "generated_at": "...",
      "sources": {
        "itviec": {
          "jobs_today": 12,
          "jobs_total_inserted": 150,
          "errors_today": 0,
          "last_run": "2024-01-15T10:30:00",
          "last_run_duration_seconds": 45.2
        },
        ...
      }
    }
    """
    today_start = datetime.combine(date.today(), datetime.min.time()).astimezone(timezone.utc)

    result: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {},
    }

    for source in KNOWN_SOURCES:
        # Jobs inserted today by this source
        today_result = await db.execute(
            select(
                func.coalesce(func.sum(CrawlLog.jobs_inserted), 0).label("jobs_today"),
                func.coalesce(func.sum(CrawlLog.errors), 0).label("errors_today"),
                func.count(CrawlLog.id).label("runs_today"),
            ).where(
                CrawlLog.source == source,
                CrawlLog.started_at >= today_start,
            )
        )
        today_row = today_result.first()

        # All-time total for this source
        total_result = await db.execute(
            select(
                func.coalesce(func.sum(CrawlLog.jobs_inserted), 0).label("total_inserted"),
            ).where(CrawlLog.source == source)
        )
        total_row = total_result.first()

        # Last run info
        last_run_result = await db.execute(
            select(
                CrawlLog.started_at,
                CrawlLog.finished_at,
                CrawlLog.duration_seconds,
                CrawlLog.jobs_inserted,
                CrawlLog.errors,
            )
            .where(CrawlLog.source == source)
            .order_by(CrawlLog.started_at.desc())
            .limit(1)
        )
        last_run = last_run_result.first()

        result["sources"][source] = {
            "jobs_today": int(today_row.jobs_today) if today_row else 0,
            "errors_today": int(today_row.errors_today) if today_row else 0,
            "runs_today": int(today_row.runs_today) if today_row else 0,
            "jobs_total_inserted": int(total_row.total_inserted) if total_row else 0,
            "last_run": last_run.started_at.isoformat() if last_run and last_run.started_at else None,
            "last_run_duration_seconds": last_run.duration_seconds if last_run else None,
            "last_run_inserted": last_run.jobs_inserted if last_run else 0,
            "last_run_errors": last_run.errors if last_run else 0,
            "status": _source_status(last_run),
        }

    return result


def _source_status(last_run) -> str:
    """Derive a human-readable status from the last CrawlLog row."""
    if last_run is None:
        return "never_run"
    # If last run had errors and no inserts -> degraded
    if last_run.errors > 0 and last_run.jobs_inserted == 0:
        return "error"
    # If last run was more than 30 minutes ago (2x interval) -> stale
    if last_run.started_at:
        age = datetime.now(timezone.utc) - last_run.started_at.replace(tzinfo=timezone.utc)
        if age > timedelta(minutes=30):
            return "stale"
    return "ok"


@router.get("/logs", summary="Recent crawl logs (all sources)")
async def get_crawl_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return the most recent crawl log entries across all sources."""
    if limit > 200:
        limit = 200

    result = await db.execute(
        select(CrawlLog)
        .order_by(CrawlLog.started_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()

    return [_crawl_log_to_dict(log) for log in logs]


@router.get("/logs/{source}", summary="Recent crawl logs for a specific source")
async def get_crawl_logs_by_source(
    source: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return the most recent crawl log entries for the given source."""
    if source not in KNOWN_SOURCES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown source '{source}'. Valid sources: {KNOWN_SOURCES}",
        )
    if limit > 200:
        limit = 200

    result = await db.execute(
        select(CrawlLog)
        .where(CrawlLog.source == source)
        .order_by(CrawlLog.started_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()

    return [_crawl_log_to_dict(log) for log in logs]


@router.get("/trend", summary="Jobs crawled per day (last 7 days)")
async def get_crawl_trend(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return daily job insertion counts per source for the past 7 days."""
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    result = await db.execute(
        select(
            func.date(CrawlLog.started_at).label("date"),
            CrawlLog.source,
            func.sum(CrawlLog.jobs_inserted).label("jobs_inserted"),
            func.sum(CrawlLog.errors).label("errors"),
        )
        .where(CrawlLog.started_at >= seven_days_ago)
        .group_by(func.date(CrawlLog.started_at), CrawlLog.source)
        .order_by(func.date(CrawlLog.started_at))
    )
    rows = result.fetchall()

    return [
        {
            "date": str(row.date),
            "source": row.source,
            "jobs_inserted": int(row.jobs_inserted or 0),
            "errors": int(row.errors or 0),
        }
        for row in rows
    ]


def _crawl_log_to_dict(log: CrawlLog) -> dict[str, Any]:
    """Serialize a CrawlLog ORM row to a JSON-safe dict."""
    return {
        "id": str(log.id),
        "source": log.source,
        "jobs_fetched": log.jobs_fetched,
        "jobs_inserted": log.jobs_inserted,
        "jobs_updated": log.jobs_updated,
        "jobs_skipped": log.jobs_skipped,
        "errors": log.errors,
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "finished_at": log.finished_at.isoformat() if log.finished_at else None,
        "duration_seconds": log.duration_seconds,
        "error_detail": log.error_detail,
    }
