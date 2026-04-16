"""
crawler/vietnamworks_crawler.py
================================
VietnamWorks-specific crawler.

VietnamWorks renders its job list via server-side HTML for search pages.
We scrape:
  - Job list page: /it-jobs?page=N
  - Job detail page: /nha-tuyen-dung/<company>/<job-slug>

Note: VietnamWorks may partially use JavaScript rendering.
      If HTML response is empty, fallback to parsing JSON-LD / meta tags.

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

import json
import logging
import time
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from crawler.base_crawler import BaseCrawler, RawJob
from crawler.config import crawler_settings
from crawler.utils import build_session

logger = logging.getLogger(__name__)

VNW_BASE_URL = "https://www.vietnamworks.com"
VNW_JOBS_PATH = "/it-jobs"


class VietnamWorksCrawler(BaseCrawler):
    SOURCE_NAME = "vietnamworks"

    def __init__(self) -> None:
        self._session = build_session()
        self._session.headers.update({
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": VNW_BASE_URL,
        })
        self._base_url = VNW_BASE_URL
        self._delay = crawler_settings.CRAWLER_REQUEST_DELAY
        self._timeout = crawler_settings.CRAWLER_TIMEOUT

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get(self, url: str) -> Optional[BeautifulSoup]:
        """Perform a GET and return BeautifulSoup, or None on failure."""
        try:
            resp = self._session.get(url, timeout=self._timeout)
            if resp.status_code == 403:
                logger.warning(f"[VietnamWorks] 403 Forbidden: {url}")
                raise PermissionError(f"HTTP 403 from {url}")
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except PermissionError:
            raise
        except Exception as exc:
            logger.warning(f"[VietnamWorks] GET failed for {url}: {exc}")
            return None

    def _list_url(self, page: int) -> str:
        if page <= 1:
            return f"{self._base_url}{VNW_JOBS_PATH}"
        return f"{self._base_url}{VNW_JOBS_PATH}?page={page}"

    def _full_url(self, href: str) -> str:
        if href.startswith("http"):
            return href
        return urljoin(self._base_url, href)

    def _extract_json_ld(self, soup: BeautifulSoup) -> list[dict]:
        """Try to extract structured job data from JSON-LD scripts."""
        json_ld_jobs = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict) and data.get("@type") in ("JobPosting", "ItemList"):
                    json_ld_jobs.append(data)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "JobPosting":
                            json_ld_jobs.append(item)
            except (json.JSONDecodeError, AttributeError):
                continue
        return json_ld_jobs

    # ── List page ─────────────────────────────────────────────────────────────

    def fetch_job_list(self, page: int = 1) -> List[RawJob]:
        """
        Scrape job cards from the VietnamWorks listing page.
        Returns a list of RawJob stubs (no description yet).
        """
        url = self._list_url(page)
        logger.info(f"[VietnamWorks] Fetching job list: {url}")

        soup = self._get(url)
        if not soup:
            logger.error(f"[VietnamWorks] Could not fetch listing page {page}")
            return []

        jobs: List[RawJob] = []

        # Try HTML selectors first — VNW job card patterns
        cards = (
            soup.select("div.job-item")
            or soup.select("div[class*='job-item']")
            or soup.select("div.job-listing-item")
            or soup.select("article.job-item")
            or soup.select("li.job-item")
        )

        if cards:
            logger.debug(f"[VietnamWorks] Found {len(cards)} job cards on page {page}")
            for card in cards:
                try:
                    stub = self._parse_card(card)
                    if stub:
                        jobs.append(stub)
                except Exception as exc:
                    logger.debug(f"[VietnamWorks] Error parsing card: {exc}")
                    continue
            if jobs:
                return jobs

        # Fallback 1: JSON-LD structured data
        json_ld_jobs = self._extract_json_ld(soup)
        if json_ld_jobs:
            logger.info(f"[VietnamWorks] Using JSON-LD fallback: {len(json_ld_jobs)} records")
            for item in json_ld_jobs:
                try:
                    stub = self._parse_json_ld(item)
                    if stub:
                        jobs.append(stub)
                except Exception as exc:
                    logger.debug(f"[VietnamWorks] JSON-LD parse error: {exc}")
            if jobs:
                return jobs

        # Fallback 2: any job title links
        anchors = soup.select(
            "h2 a[href*='/viec-lam/'], h3 a[href*='/viec-lam/'], "
            "a[class*='job'], a[href*='job']"
        )
        logger.warning(f"[VietnamWorks] All selectors failed, fallback found {len(anchors)} links")
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

    def _parse_card(self, card) -> Optional[RawJob]:
        """Parse a single job card element into a RawJob stub."""

        # ── Title + URL ────────────────────────────────────────────────────
        title_el = (
            card.select_one("h2.title a")
            or card.select_one("h3.title a")
            or card.select_one("a.job-title")
            or card.select_one("a[data-job-title]")
            or card.select_one("h2 a")
            or card.select_one("a[href*='/viec-lam/']")
        )
        if not title_el:
            return None

        job_title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        if not href or len(job_title) < 3:
            return None
        job_url = self._full_url(href)

        # ── Company ────────────────────────────────────────────────────────
        company_el = (
            card.select_one("div.company-name a")
            or card.select_one("a.company-name")
            or card.select_one("span.company-name")
            or card.select_one("div.employer a")
            or card.select_one("p.company")
        )
        company = company_el.get_text(strip=True) if company_el else "Unknown"

        # ── Location ───────────────────────────────────────────────────────
        location_el = (
            card.select_one("span.location")
            or card.select_one("div.location")
            or card.select_one("span.address")
            or card.select_one("div.city")
        )
        location = location_el.get_text(strip=True) if location_el else None

        return RawJob(
            job_title=job_title,
            company=company,
            job_url=job_url,
            source=self.SOURCE_NAME,
            location=location,
        )

    def _parse_json_ld(self, item: dict) -> Optional[RawJob]:
        """Parse a JSON-LD JobPosting object into a RawJob stub."""
        title = item.get("title") or item.get("name")
        url = item.get("url") or item.get("sameAs")
        if not title or not url:
            return None

        company = "Unknown"
        hiring_org = item.get("hiringOrganization")
        if isinstance(hiring_org, dict):
            company = hiring_org.get("name", "Unknown")
        elif isinstance(hiring_org, str):
            company = hiring_org

        location = None
        job_location = item.get("jobLocation")
        if isinstance(job_location, dict):
            address = job_location.get("address")
            if isinstance(address, dict):
                location = address.get("addressLocality") or address.get("addressRegion")
            elif isinstance(address, str):
                location = address

        return RawJob(
            job_title=title,
            company=company,
            job_url=self._full_url(url),
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
        logger.debug(f"[VietnamWorks] Fetching detail: {raw_job.job_url}")

        soup = self._get(raw_job.job_url)
        if not soup:
            logger.warning(f"[VietnamWorks] Could not fetch detail for {raw_job.job_url}")
            return raw_job

        # ── Try JSON-LD for description first ─────────────────────────────
        json_ld_jobs = self._extract_json_ld(soup)
        for item in json_ld_jobs:
            desc = item.get("description")
            if desc:
                raw_job.description = desc
                break

        # ── HTML description fallback ──────────────────────────────────────
        if not raw_job.description:
            desc_el = (
                soup.select_one("div.job-description")
                or soup.select_one("div#job-description")
                or soup.select_one("div.description-content")
                or soup.select_one("div[class*='job-description']")
                or soup.select_one("div.detail-row")
            )

            if desc_el:
                raw_job.description = str(desc_el)
            else:
                paragraphs = soup.select("main p, main li, section.content p")
                if paragraphs:
                    raw_job.description = " ".join(p.get_text(separator=" ") for p in paragraphs)

        # ── Skills ──────────────────────────────────────────────────────────
        skill_tags = (
            soup.select("span.tag")
            or soup.select("a.skill")
            or soup.select("div.skill-tag span")
            or soup.select("ul.tag-list li")
        )
        if skill_tags:
            raw_job.skills_raw = [t.get_text(strip=True) for t in skill_tags if t.get_text(strip=True)]

        # ── Company override ───────────────────────────────────────────────
        company_el = (
            soup.select_one("h2.company-name")
            or soup.select_one("div.company-title a")
            or soup.select_one("a[data-company-name]")
        )
        if company_el and raw_job.company == "Unknown":
            raw_job.company = company_el.get_text(strip=True)

        # ── Location override ──────────────────────────────────────────────
        if not raw_job.location:
            loc_el = (
                soup.select_one("span.location")
                or soup.select_one("div.job-detail-location")
                or soup.select_one("span.address")
            )
            if loc_el:
                raw_job.location = loc_el.get_text(strip=True)

        return raw_job
