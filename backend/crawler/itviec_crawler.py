"""
crawler/itviec_crawler.py
=========================
ITviec-specific crawler.

ITviec renders its job list via server-side HTML.
We scrape:
  - Job list page: /it-jobs?page=N
  - Job detail page: /it-jobs/<slug>

Strategy:
  1. GET listing page -> parse job cards -> extract stubs
  2. For each stub -> GET detail page -> parse full description

Anti-blocking measures:
  - Realistic browser headers (see utils.build_session)
  - Configurable delay between requests
  - Retry with exponential back-off on 429/5xx
"""
from __future__ import annotations

import logging
import time
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from crawler.base_crawler import BaseCrawler, RawJob
from crawler.config import crawler_settings
from crawler.utils import build_session, clean_html

logger = logging.getLogger(__name__)


class ITviecCrawler(BaseCrawler):
    SOURCE_NAME = "itviec"

    def __init__(self) -> None:
        self._session = build_session()
        self._base_url = crawler_settings.ITVIEC_BASE_URL
        self._jobs_path = crawler_settings.ITVIEC_JOBS_PATH
        self._delay = crawler_settings.CRAWLER_REQUEST_DELAY
        self._timeout = crawler_settings.CRAWLER_TIMEOUT

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get(self, url: str) -> Optional[BeautifulSoup]:
        """Perform a GET and return BeautifulSoup, or None on failure."""
        try:
            resp = self._session.get(url, timeout=self._timeout)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except Exception as exc:
            logger.warning(f"[ITviec] GET failed for {url}: {exc}")
            return None

    def _list_url(self, page: int) -> str:
        return f"{self._base_url}{self._jobs_path}?page={page}"

    def _full_url(self, href: str) -> str:
        if href.startswith("http"):
            return href
        return urljoin(self._base_url, href)

    # ── List page ─────────────────────────────────────────────────────────────

    def fetch_job_list(self, page: int = 1) -> List[RawJob]:
        """
        Scrape job cards from the ITviec listing page.
        Returns a list of RawJob stubs (no description yet).
        """
        url = self._list_url(page)
        logger.info(f"[ITviec] Fetching job list: {url}")

        soup = self._get(url)
        if not soup:
            logger.error(f"[ITviec] Could not fetch listing page {page}")
            return []

        jobs: List[RawJob] = []

        # ITviec job cards: <div class="job_content"> or <div class="ipt-jobs">
        # Multiple selectors for resilience against markup changes
        cards = (
            soup.select("div.job_content")
            or soup.select("div[data-controller='job-card']")
            or soup.select("div.job-card")
            or soup.select("article.job")
        )

        if not cards:
            # Fallback: find all job links in common patterns
            cards = soup.select("h2.title a, h3.title a")
            logger.warning(f"[ITviec] Primary selectors not found, fallback found {len(cards)} links")
            # Parse links directly as minimal stubs
            for anchor in cards:
                href = anchor.get("href", "")
                if not href:
                    continue
                job_url = self._full_url(href)
                stub = RawJob(
                    job_title=anchor.get_text(strip=True),
                    company="Unknown",
                    job_url=job_url,
                    source=self.SOURCE_NAME,
                )
                jobs.append(stub)
            return jobs

        logger.debug(f"[ITviec] Found {len(cards)} job cards on page {page}")

        for card in cards:
            try:
                stub = self._parse_card(card)
                if stub:
                    jobs.append(stub)
            except Exception as exc:
                logger.debug(f"[ITviec] Error parsing card: {exc}")
                continue

        return jobs

    def _parse_card(self, card) -> Optional[RawJob]:
        """Parse a single job card element into a RawJob stub."""

        # ── Title + URL ────────────────────────────────────────────────────
        title_el = (
            card.select_one("h2.title a")
            or card.select_one("h3.title a")
            or card.select_one("a.job-title")
            or card.select_one("a[data-job-title]")
            or card.select_one("h2 a")
            or card.select_one("h3 a")
        )
        if not title_el:
            return None

        job_title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        if not href:
            return None
        job_url = self._full_url(href)

        # ── Company ────────────────────────────────────────────────────────
        company_el = (
            card.select_one("div.employer-name a")
            or card.select_one("a.company-name")
            or card.select_one("span.company-name")
            or card.select_one("div.company a")
            or card.select_one("p.company-name")
        )
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        # ── Location ───────────────────────────────────────────────────────
        location_el = (
            card.select_one("svg.icon-map-pin ~ span")
            or card.select_one("span.address")
            or card.select_one("div.location")
            or card.select_one("span.location")
        )
        location = location_el.get_text(strip=True) if location_el else None

        # ── Posted time ────────────────────────────────────────────────────
        time_el = (
            card.select_one("time")
            or card.select_one("span.date")
            or card.select_one("p.date-posted")
        )
        posted_time = None
        if time_el:
            posted_time = time_el.get("datetime") or time_el.get_text(strip=True)

        return RawJob(
            job_title=job_title,
            company=company,
            job_url=job_url,
            source=self.SOURCE_NAME,
            location=location,
            posted_time=posted_time,
        )

    # ── Detail page ───────────────────────────────────────────────────────────

    def fetch_job_detail(self, raw_job: RawJob) -> RawJob:
        """
        Visit the job detail page and extract full description.
        Modifies raw_job in place and returns it.
        """
        time.sleep(self._delay)   # polite delay
        logger.debug(f"[ITviec] Fetching detail: {raw_job.job_url}")

        soup = self._get(raw_job.job_url)
        if not soup:
            logger.warning(f"[ITviec] Could not fetch detail for {raw_job.job_url}")
            return raw_job

        # ── Full description block ─────────────────────────────────────────
        desc_el = (
            soup.select_one("div.job-description")
            or soup.select_one("div#job-description")
            or soup.select_one("div.description")
            or soup.select_one("section.job-details")
            or soup.select_one("div.job_description")
            or soup.select_one("div[data-controller='jobs-show']")
        )

        if desc_el:
            raw_job.description = str(desc_el)
        else:
            # Fallback: grab all meaningful paragraphs
            paragraphs = soup.select("main p, main li, main h3, main h4")
            if paragraphs:
                raw_job.description = " ".join(p.get_text(separator=" ") for p in paragraphs)

        # ── Skills (if explicitly listed) ──────────────────────────────────
        skill_tags = (
            soup.select("a.tag--skill")
            or soup.select("span.tag-skill")
            or soup.select("div.skill-tags a")
            or soup.select("ul.tag-list li")
        )
        if skill_tags:
            raw_job.skills_raw = [t.get_text(strip=True) for t in skill_tags if t.get_text(strip=True)]

        # ── Company override (detail may have richer data) ─────────────────
        company_el = (
            soup.select_one("div.company-title a")
            or soup.select_one("h2.employer-name")
            or soup.select_one("a[data-company]")
        )
        if company_el:
            raw_job.company = company_el.get_text(strip=True)

        # ── Location override ──────────────────────────────────────────────
        if not raw_job.location:
            loc_el = (
                soup.select_one("svg.icon-map-pin ~ span")
                or soup.select_one("span.address")
                or soup.select_one("div.job-location")
            )
            if loc_el:
                raw_job.location = loc_el.get_text(strip=True)

        return raw_job
