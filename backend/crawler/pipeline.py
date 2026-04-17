"""
crawler/pipeline.py
===================
CrawlerPipeline — Orchestrates the full crawl cycle for a given source.

Pipeline stages:
  1. Fetch job list  (page 1..N)
  2. Deduplicate     (skip already-seen links)
  3. Fetch job detail (for each new job)
  4. Clean HTML
  5. Extract skills
  6. Generate embedding  (optional, via SBERT)
  7. Upsert to DB (+ triggers recommendation matching for new jobs)
  8. Save CrawlLog record
  9. Fire alert if error rate is high (Task 6)

Emits structured JSON log output for monitoring + observability.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.preprocessing import clean_text
from crawler.base_crawler import BaseCrawler, RawJob
from crawler.config import crawler_settings
from crawler.database import get_crawled_links, upsert_job
from crawler.utils import extract_skills

logger = logging.getLogger(__name__)


# ── Structured JSON logger ────────────────────────────────────────────────────
def _log_json(level: str, event: str, **kwargs) -> None:
    """Emit a structured JSON log record for monitoring pipelines."""
    payload = json.dumps({"event": event, "level": level, **kwargs}, default=str)
    if level == "info":
        logger.info(payload)
    elif level == "warning":
        logger.warning(payload)
    elif level == "error":
        logger.error(payload)
    else:
        logger.debug(payload)


@dataclass
class CrawlResult:
    """Summary of a single crawl run."""
    source: str
    total_fetched: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    error_urls: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def log_summary(self) -> None:
        border = "=" * 60
        logger.info(border)
        logger.info(f"[Crawler] Run complete — source: {self.source}")
        logger.info(f"  Fetched : {self.total_fetched}")
        logger.info(f"  Inserted: {self.inserted}")
        logger.info(f"  Updated : {self.updated}")
        logger.info(f"  Skipped : {self.skipped}")
        logger.info(f"  Errors  : {self.errors}")
        logger.info(f"  Duration: {self.duration_seconds:.1f}s")
        if self.error_urls:
            logger.warning(f"  Failed URLs ({len(self.error_urls)}): {self.error_urls[:5]}")
        logger.info(border)

        # Structured JSON summary for log aggregation
        _log_json(
            level="info",
            event="crawl_complete",
            source=self.source,
            jobs_fetched=self.total_fetched,
            jobs_inserted=self.inserted,
            jobs_updated=self.updated,
            jobs_skipped=self.skipped,
            errors=self.errors,
            duration_seconds=round(self.duration_seconds, 2),
        )


class CrawlerPipeline:
    """
    Runs the full crawl → process → store pipeline.

    Usage (from async context):
        pipeline = CrawlerPipeline(ITviecCrawler(), session)
        result = await pipeline.run(pages=1)
    """

    def __init__(self, crawler: BaseCrawler, session: AsyncSession) -> None:
        self._crawler = crawler
        self._session = session

    async def run(
        self,
        pages: int = 1,
        max_jobs: Optional[int] = None,
    ) -> CrawlResult:
        """
        Execute the full crawl pipeline.

        Args:
            pages:    Number of listing pages to crawl (default 1 = latest)
            max_jobs: Hard cap on jobs processed per run

        Returns:
            CrawlResult summary dataclass
        """
        source = self._crawler.get_source_name()
        max_jobs = max_jobs or crawler_settings.CRAWLER_MAX_JOBS_PER_RUN
        result = CrawlResult(source=source)
        start_time = time.monotonic()

        _log_json(
            level="info",
            event="crawl_start",
            source=source,
            pages=pages,
            max_jobs=max_jobs,
        )

        # ── Stage 1: Load existing links for dedup ─────────────────────────
        try:
            seen_links = await get_crawled_links(self._session)
        except Exception as exc:
            logger.error(f"[Crawler] Failed to load seen links: {exc}")
            seen_links = set()

        # ── Stage 2: Fetch list pages ──────────────────────────────────────
        stubs: List[RawJob] = []
        for page in range(1, pages + 1):
            try:
                page_stubs = self._crawler.fetch_job_list(page=page)
                stubs.extend(page_stubs)
                logger.info(f"[Crawler] Page {page}: {len(page_stubs)} stubs fetched")
            except PermissionError as pe:
                # HTTP 403 — alert and abort this source
                logger.error(f"[Crawler] 403 blocked on page {page}: {pe}")
                result.errors += 1
                _log_json(level="error", event="crawl_blocked_403", source=source, page=page)
                break  # stop fetching more pages for this source
            except Exception as exc:
                logger.error(f"[Crawler] Error fetching list page {page}: {exc}")
                result.errors += 1

        result.total_fetched = len(stubs)

        # ── Stage 3: Filter to unseen + apply cap ─────────────────────────
        new_stubs = [s for s in stubs if s.job_url not in seen_links]
        if len(new_stubs) > max_jobs:
            logger.info(f"[Crawler] Capping to {max_jobs} (found {len(new_stubs)} new)")
            new_stubs = new_stubs[:max_jobs]

        result.skipped = len(stubs) - len(new_stubs)
        logger.info(f"[Crawler] {len(new_stubs)} new jobs to process ({result.skipped} skipped/duplicate)")

        # ── Stage 4–7: Detail + clean + skills + embed + upsert ───────────
        for stub in new_stubs:
            try:
                await self._process_job(stub, result)
            except Exception as exc:
                logger.error(f"[Crawler] Unhandled error for {stub.job_url}: {exc}")
                result.errors += 1
                result.error_urls.append(stub.job_url)

        # ── Check error rate and alert if high ─────────────────────────────
        if len(new_stubs) > 0:
            error_rate = result.errors / max(len(new_stubs), 1)
            if error_rate > 0.5:
                _log_json(level="warning", event="high_error_rate", source=source, error_rate=round(error_rate, 2))

        # ── Commit ─────────────────────────────────────────────────────────
        try:
            await self._session.commit()
        except Exception as exc:
            logger.error(f"[Crawler] Commit failed: {exc}")
            await self._session.rollback()
            result.errors += 1

        result.duration_seconds = time.monotonic() - start_time
        result.log_summary()

        # ── Stage 8: Save CrawlLog record ─────────────────────────────────
        await self._save_crawl_log(result)

        return result

    async def _process_job(self, stub: RawJob, result: CrawlResult) -> None:
        """Process a single job stub through stages 4–7."""

        # Stage 4: Fetch detail
        try:
            job = self._crawler.fetch_job_detail(stub)
        except PermissionError:
            # 403 on detail page — count as error but keep going
            logger.warning(f"[Crawler] 403 on detail: {stub.job_url}")
            result.errors += 1
            result.error_urls.append(stub.job_url)
            job = stub  # proceed with partial data
        except Exception as exc:
            logger.warning(f"[Crawler] Detail fetch failed for {stub.job_url}: {exc}")
            result.errors += 1
            result.error_urls.append(stub.job_url)
            job = stub  # proceed with partial data

        # Stage 5: Clean HTML
        raw_desc = job.description or ""
        cleaned = clean_text(raw_desc)  # uses existing app.ml.preprocessing

        # Stage 6: Extract skills
        explicit_skills = job.skills_raw or []
        extracted_skills = extract_skills(cleaned)
        all_skills = sorted(set(explicit_skills) | set(extracted_skills))

        # Stage 7: Generate embedding (optional)
        embedding = None
        if crawler_settings.CRAWLER_EMBED_ON_INSERT and cleaned:
            try:
                from app.services.embedding_service import embedding_service
                emb_array = embedding_service.encode_batch([cleaned], batch_size=1)
                embedding = emb_array[0].tolist()
            except Exception as exc:
                logger.warning(f"[Crawler] Embedding failed for {job.job_url}: {exc}")

        # Build DB payload
        job_data = {
            "position_title": job.job_title,
            "company": job.company,
            "location": job.location,
            "link": job.job_url,
            "description": raw_desc,
            "cleaned_description": cleaned,
            "skills": all_skills,
            "source": job.source,
            "embedding": embedding,
        }

        # Stage 8: Upsert (also triggers recommendation matching for new jobs)
        inserted, updated = await upsert_job(self._session, job_data)
        if inserted:
            result.inserted += 1
            _log_json(
                level="info",
                event="job_inserted",
                source=job.source,
                title=job.job_title,
                link=job.job_url,
            )
        elif updated:
            result.updated += 1
        else:
            result.skipped += 1

    async def _save_crawl_log(self, result: CrawlResult) -> None:
        """Persist a CrawlLog record for monitoring (best-effort, non-critical)."""
        try:
            from app.database import AsyncSessionLocal
            from app.models.crawl_log import CrawlLog

            error_preview = (
                "; ".join(result.error_urls[:5])
                if result.error_urls
                else None
            )

            log_record = CrawlLog(
                source=result.source,
                jobs_fetched=result.total_fetched,
                jobs_inserted=result.inserted,
                jobs_updated=result.updated,
                jobs_skipped=result.skipped,
                errors=result.errors,
                started_at=result.started_at,
                finished_at=datetime.now(timezone.utc),
                duration_seconds=round(result.duration_seconds, 2),
                error_detail=error_preview,
            )

            # Use a fresh session to avoid conflicts with the main session's state
            async with AsyncSessionLocal() as log_session:
                log_session.add(log_record)
                await log_session.commit()

            logger.debug(f"[Crawler] CrawlLog saved for source={result.source}")
        except Exception as exc:
            # Non-critical: never let logging failure break the crawler
            logger.warning(f"[Crawler] Failed to save CrawlLog: {exc}")
