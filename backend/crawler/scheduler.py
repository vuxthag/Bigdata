"""
crawler/scheduler.py
====================
Register all crawlers as APScheduler interval jobs.

Call register_crawler_jobs(scheduler) once during app startup.
Each source runs independently every CRAWLER_INTERVAL_MINUTES minutes,
staggered by source to avoid hitting all sites simultaneously.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from crawler.config import crawler_settings

logger = logging.getLogger(__name__)


async def _run_source_job(source: str) -> None:
    """
    APScheduler async job — runs the full crawl pipeline for one source.
    Imports are deferred to avoid circular imports at module load.
    """
    from app.database import AsyncSessionLocal
    from crawler.pipeline import CrawlerPipeline

    logger.info(f"[Scheduler] Crawler job triggered for source={source}")

    try:
        # Build the appropriate crawler
        if source == "itviec":
            from crawler.itviec_crawler import ITviecCrawler
            crawler = ITviecCrawler()
        elif source == "topcv":
            from crawler.topcv_crawler import TopCVCrawler
            crawler = TopCVCrawler()
        elif source == "vietnamworks":
            from crawler.vietnamworks_crawler import VietnamWorksCrawler
            crawler = VietnamWorksCrawler()
        else:
            logger.error(f"[Scheduler] Unknown source: {source}")
            return

        async with AsyncSessionLocal() as session:
            pipeline = CrawlerPipeline(crawler, session)
            result = await pipeline.run(
                pages=crawler_settings.CRAWLER_PAGES_PER_RUN,
                max_jobs=crawler_settings.CRAWLER_MAX_JOBS_PER_RUN,
            )
            logger.info(
                f"[Scheduler] [{source}] Finished — "
                f"inserted={result.inserted}, updated={result.updated}, "
                f"skipped={result.skipped}, errors={result.errors}"
            )
    except Exception as exc:
        logger.error(f"[Scheduler] [{source}] Crawler job failed: {exc}", exc_info=True)


def register_crawler_jobs(scheduler: AsyncIOScheduler) -> None:
    """
    Register all crawler sources as staggered interval jobs.

    Stagger offsets (minutes after scheduler start):
      - ITviec   : starts immediately (offset 0)
      - TopCV    : starts 3 min later (offset 3)
      - VietnamWorks: starts 6 min later (offset 6)

    All run every CRAWLER_INTERVAL_MINUTES minutes.
    This prevents hitting all job sites at the exact same second.
    """
    interval = crawler_settings.CRAWLER_INTERVAL_MINUTES

    sources = [
        ("itviec",       "itviec_crawler_job",       0),
        ("topcv",        "topcv_crawler_job",         3),
        ("vietnamworks", "vietnamworks_crawler_job",  6),
    ]

    for source, job_id, offset_minutes in sources:
        scheduler.add_job(
            _run_source_job,
            args=[source],
            trigger="interval",
            minutes=interval,
            start_date=None,       # APScheduler computes start based on offset below
            id=job_id,
            replace_existing=True,
            max_instances=1,        # prevent overlap if a run is slow
            misfire_grace_time=120, # 2 min grace before skipping misfired run
            kwargs={},
        )
        # Apply stagger by modifying the next run time after adding
        job = scheduler.get_job(job_id)
        if job and offset_minutes > 0:
            from datetime import datetime, timedelta, timezone
            new_run_time = datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)
            job.modify(next_run_time=new_run_time)

        logger.info(f"[Scheduler] {source} crawler registered — interval={interval}min, offset={offset_minutes}min")
