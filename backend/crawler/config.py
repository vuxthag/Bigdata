"""
crawler/config.py
=================
Crawler-specific settings loaded from environment variables.
All values have sane defaults so the system works out of the box.
"""
from __future__ import annotations

import os


class CrawlerSettings:
    """Reads crawler config from environment variables with safe defaults."""

    # ── Schedule ────────────────────────────────────────────────────────────
    CRAWLER_INTERVAL_MINUTES: int = int(os.getenv("CRAWLER_INTERVAL_MINUTES", "10"))

    # ── Per-run limits ──────────────────────────────────────────────────────
    CRAWLER_MAX_JOBS_PER_RUN: int = int(os.getenv("CRAWLER_MAX_JOBS_PER_RUN", "30"))
    CRAWLER_PAGES_PER_RUN: int = int(os.getenv("CRAWLER_PAGES_PER_RUN", "2"))

    # ── Politeness ──────────────────────────────────────────────────────────
    # Delay in seconds between consecutive HTTP requests
    CRAWLER_REQUEST_DELAY: float = float(os.getenv("CRAWLER_REQUEST_DELAY", "1.5"))
    CRAWLER_MAX_RETRIES: int = int(os.getenv("CRAWLER_MAX_RETRIES", "3"))
    CRAWLER_BACKOFF_FACTOR: float = float(os.getenv("CRAWLER_BACKOFF_FACTOR", "2.0"))
    CRAWLER_TIMEOUT: int = int(os.getenv("CRAWLER_TIMEOUT", "15"))

    # ── Sources ─────────────────────────────────────────────────────────────
    ITVIEC_BASE_URL: str = os.getenv("ITVIEC_BASE_URL", "https://itviec.com")
    ITVIEC_JOBS_PATH: str = os.getenv("ITVIEC_JOBS_PATH", "/it-jobs")

    # ── Embedding ───────────────────────────────────────────────────────────
    # Whether to generate SBERT embeddings immediately after inserting
    CRAWLER_EMBED_ON_INSERT: bool = os.getenv("CRAWLER_EMBED_ON_INSERT", "true").lower() == "true"


crawler_settings = CrawlerSettings()
