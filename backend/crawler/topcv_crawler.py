"""
crawler/topcv_crawler.py
========================
TopCV-specific crawler.

TopCV renders its job list via server-side HTML.
We scrape:
  - Job list page: /tim-viec-lam-it?page=N
  - Job detail page: /viec-lam/<slug>

Strategy:
  1. GET listing page -> parse job cards -> extract stubs
  2. For each stub -> GET detail page -> parse full description

Anti-blocking measures:
  - Realistic browser headers (see utils.build_session)
  - Configurable delay between requests
  - Retry with exponential back-off on 429/5xx
  - Multiple fallback CSS selectors for HTML changes resilience
"""
from __future__ import annotations

import logging
import time
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from crawler.base_crawler import BaseCrawler, RawJob
from crawler.config import crawler_settings
from crawler.utils import build_session

logger = logging.getLogger(__name__)

TOPCV_BASE_URL = "https://www.topcv.vn"
TOPCV_JOBS_PATH = "/tim-viec-lam-it"


class TopCVCrawler(BaseCrawler):
    SOURCE_NAME = "topcv"

    def __init__(self) -> None:
        self._session = build_session()
        # TopCV needs Vietnamese Accept-Language header
        self._session.headers.update({
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": TOPCV_BASE_URL,
        })
        self._base_url = TOPCV_BASE_URL
        self._delay = crawler_settings.CRAWLER_REQUEST_DELAY
        self._timeout = crawler_settings.CRAWLER_TIMEOUT

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get(self, url: str) -> Optional[BeautifulSoup]:
        """Perform a GET and return BeautifulSoup, or None on failure."""
        try:
            resp = self._session.get(url, timeout=self._timeout)
            if resp.status_code == 403:
                logger.warning(f"[TopCV] 403 Forbidden: {url}")
                raise PermissionError(f"HTTP 403 from {url}")
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except PermissionError:
            raise
        except Exception as exc:
            logger.warning(f"[TopCV] GET failed for {url}: {exc}")
            return None

    def _list_url(self, page: int) -> str:
        if page <= 1:
            return f"{self._base_url}{TOPCV_JOBS_PATH}"
        return f"{self._base_url}{TOPCV_JOBS_PATH}?page={page}"

    def _full_url(self, href: str) -> str:
        if href.startswith("http"):
            return href
        return urljoin(self._base_url, href)

    # ── List page ─────────────────────────────────────────────────────────────

    def fetch_job_list(self, page: int = 1) -> List[RawJob]:
        """
        Scrape job cards from the TopCV listing page.
        Returns a list of RawJob stubs (no description yet).
        """
        url = self._list_url(page)
        logger.info(f"[TopCV] Fetching job list: {url}")

        soup = self._get(url)
        if not soup:
            logger.error(f"[TopCV] Could not fetch listing page {page}")
            return []

        jobs: List[RawJob] = []

        # TopCV uses several card container patterns — try all
        cards = (
            soup.select("div.job-item-search-result")
            or soup.select("div.job-item")
            or soup.select("div[data-job-id]")
            or soup.select("div.job-list-item")
            or soup.select("article.job-item")
        )

        if not cards:
            # Fallback: grab all job title links
            anchors = soup.select("h3.title a, h2.title a, a.job-name, a[data-job-title]")
            logger.warning(f"[TopCV] Primary selectors not found, fallback found {len(anchors)} links")
            for anchor in anchors:
                href = anchor.get("href", "")
                if not href:
                    continue
                stub = RawJob(
                    job_title=anchor.get_text(strip=True),
                    company="Unknown",
                    job_url=self._full_url(href),
                    source=self.SOURCE_NAME,
                )
                jobs.append(stub)
            return jobs

        logger.debug(f"[TopCV] Found {len(cards)} job cards on page {page}")

        for card in cards:
            try:
                stub = self._parse_card(card)
                if stub:
                    jobs.append(stub)
            except Exception as exc:
                logger.debug(f"[TopCV] Error parsing card: {exc}")
                continue

        return jobs

    def _parse_card(self, card) -> Optional[RawJob]:
        """Parse a single job card element into a RawJob stub."""

        # ── Title + URL ────────────────────────────────────────────────────
        title_el = (
            card.select_one("h3.title a")
            or card.select_one("h2.title a")
            or card.select_one("a.job-name")
            or card.select_one("a[data-job-title]")
            or card.select_one("h3 a")
            or card.select_one("div.title a")
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
            card.select_one("div.company-name a")
            or card.select_one("a.company-name")
            or card.select_one("span.company-name")
            or card.select_one("div.company a")
            or card.select_one("a[data-company-name]")
            or card.select_one("div.employer a")
        )
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        # ── Location ───────────────────────────────────────────────────────
        location_el = (
            card.select_one("label.address")
            or card.select_one("span.address")
            or card.select_one("div.location")
            or card.select_one("span.location")
            or card.select_one("div.city-text")
        )
        location = location_el.get_text(strip=True) if location_el else None

        return RawJob(
            job_title=job_title,
            company=company,
            job_url=job_url,
            source=self.SOURCE_NAME,
            location=location,
        )

    # ── Detail page ───────────────────────────────────────────────────────────

    def fetch_job_detail(self, raw_job: RawJob) -> RawJob:
        """
        Visit the job detail page and extract full description.
        Modifies raw_job in place and returns it.
        """
        time.sleep(self._delay)  # polite delay
        logger.debug(f"[TopCV] Fetching detail: {raw_job.job_url}")

        soup = self._get(raw_job.job_url)
        if not soup:
            logger.warning(f"[TopCV] Could not fetch detail for {raw_job.job_url}")
            return raw_job

        # ── Full description block ─────────────────────────────────────────
        desc_el = (
            soup.select_one("div.job-description")
            or soup.select_one("div#job-description")
            or soup.select_one("div.description")
            or soup.select_one("div.job-detail__information-detail")
            or soup.select_one("div.box-category-info")
            or soup.select_one("section.job-details")
        )

        if desc_el:
            raw_job.description = str(desc_el)
        else:
            # Fallback: grab all meaningful paragraphs from main content
            paragraphs = soup.select("main p, main li, div.content p, div.content li")
            if paragraphs:
                raw_job.description = " ".join(p.get_text(separator=" ") for p in paragraphs)

        # ── Requirements (separate section if available) ───────────────────
        req_el = (
            soup.select_one("div.job-requirement")
            or soup.select_one("div#job-requirement")
            or soup.select_one("section.requirements")
        )
        if req_el:
            raw_job.requirements = req_el.get_text(separator="\n", strip=True)

        # ── Skills (if explicitly listed) ──────────────────────────────────
        skill_tags = (
            soup.select("div.skill-tag a")
            or soup.select("span.tag-item")
            or soup.select("a.skill-tag")
            or soup.select("div.box-skill span")
            or soup.select("ul.tag-list li")
        )
        if skill_tags:
            raw_job.skills_raw = [t.get_text(strip=True) for t in skill_tags if t.get_text(strip=True)]

        # ── Company override ───────────────────────────────────────────────
        company_el = (
            soup.select_one("div.company-name a")
            or soup.select_one("h2.company-name")
            or soup.select_one("a[data-company-name]")
        )
        if company_el and raw_job.company == "Unknown":
            raw_job.company = company_el.get_text(strip=True)

        # ── Location override ──────────────────────────────────────────────
        if not raw_job.location:
            loc_el = (
                soup.select_one("span.address")
                or soup.select_one("label.address")
                or soup.select_one("div.job-detail__info--location")
            )
            if loc_el:
                raw_job.location = loc_el.get_text(strip=True)

        return raw_job
