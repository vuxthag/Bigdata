"""
crawler/scheduler.py
====================
Register VietnamWorks crawler as an APScheduler interval job.
Only VietnamWorks is used as the job data source.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from crawler.config import crawler_settings

logger = logging.getLogger(__name__)


async def _run_source_job(source: str) -> None:
    """APScheduler async job — runs the full crawl pipeline for VietnamWorks."""
    from app.database import AsyncSessionLocal
    from crawler.pipeline import CrawlerPipeline

    logger.info(f"[Scheduler] Crawler job triggered for source={source}")

    try:
        from crawler.vietnamworks_crawler import VietnamWorksCrawler
        crawler = VietnamWorksCrawler()

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
    """Register VietnamWorks crawler as a scheduled interval job."""
    interval = crawler_settings.CRAWLER_INTERVAL_MINUTES

    scheduler.add_job(
        _run_source_job,
        args=["vietnamworks"],
        trigger="interval",
        minutes=interval,
        id="vietnamworks_crawler_job",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=120,
    )

    logger.info(f"[Scheduler] VietnamWorks crawler registered — interval={interval}min")
