"""
crawler/main.py
===============
Standalone CLI entry point for running the crawler manually or from cron.

Usage:
    # From backend/ directory:
    python -m crawler.main
    python -m crawler.main --source itviec --pages 2
    python -m crawler.main --source topcv --pages 1
    python -m crawler.main --source all --pages 1

Cron example (every 10 minutes):
    */10 * * * * cd /path/to/backend && python -m crawler.main >> logs/crawler.log 2>&1
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import os

# Ensure the backend/ folder is on sys.path when running as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("crawler.main")

SUPPORTED_SOURCES = ["itviec", "topcv", "vietnamworks", "all"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Job Crawler — fetch new job postings from job platforms"
    )
    parser.add_argument(
        "--source",
        choices=SUPPORTED_SOURCES,
        default="all",
        help="Job source to crawl (default: all)",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=None,
        help="Number of listing pages to crawl (default: from CRAWLER_PAGES_PER_RUN env)",
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=None,
        help="Max jobs to process per run (default: from CRAWLER_MAX_JOBS_PER_RUN env)",
    )
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="Skip embedding generation (faster, for testing)",
    )
    return parser.parse_args()


def _build_crawler(source: str):
    """Instantiate and return the correct crawler for a given source name."""
    if source == "itviec":
        from crawler.itviec_crawler import ITviecCrawler
        return ITviecCrawler()
    elif source == "topcv":
        from crawler.topcv_crawler import TopCVCrawler
        return TopCVCrawler()
    elif source == "vietnamworks":
        from crawler.vietnamworks_crawler import VietnamWorksCrawler
        return VietnamWorksCrawler()
    else:
        raise ValueError(f"Unknown source: {source}")


async def run_source(
    source: str,
    pages: int,
    max_jobs: int,
    session,
) -> None:
    """Run the crawl pipeline for a single source."""
    from crawler.pipeline import CrawlerPipeline

    try:
        crawler = _build_crawler(source)
    except ValueError as e:
        logger.error(f"[Main] {e}")
        return

    pipeline = CrawlerPipeline(crawler, session)
    result = await pipeline.run(pages=pages, max_jobs=max_jobs)

    if result.errors > 0 and result.inserted == 0 and result.updated == 0:
        logger.warning(f"[Main] [{source}] Run completed with errors and no new data")


async def main_async(args: argparse.Namespace) -> int:
    """Async entrypoint — sets up DB session and runs the pipeline(s)."""
    from app.database import AsyncSessionLocal, init_db
    from crawler.config import crawler_settings

    # Optionally disable embedding for this run
    if args.no_embed:
        crawler_settings.CRAWLER_EMBED_ON_INSERT = False
        logger.info("[Main] Embedding disabled for this run")

    pages = args.pages or crawler_settings.CRAWLER_PAGES_PER_RUN
    max_jobs = args.max_jobs or crawler_settings.CRAWLER_MAX_JOBS_PER_RUN

    sources = (
        ["itviec", "topcv", "vietnamworks"]
        if args.source == "all"
        else [args.source]
    )

    logger.info(f"[Main] Sources={sources}, pages={pages}, max_jobs={max_jobs}")

    # Initialize DB (safe: CREATE IF NOT EXISTS)
    logger.info("[Main] Initializing database...")
    await init_db()

    # Run each source sequentially (simpler, lower memory profile)
    async with AsyncSessionLocal() as session:
        for source in sources:
            logger.info(f"[Main] === Starting source: {source} ===")
            await run_source(source, pages, max_jobs, session)

    return 0


def main() -> None:
    args = parse_args()
    exit_code = asyncio.run(main_async(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
