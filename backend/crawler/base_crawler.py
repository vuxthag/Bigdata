"""
crawler/base_crawler.py
=======================
Abstract base class for all job source crawlers.
New sources (TopCV, VietnamWorks) must subclass BaseCrawler
and implement the two abstract methods.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RawJob:
    """
    Normalized job data returned by any crawler.
    Fields are optional where not all sources provide them.
    """
    job_title: str
    company: str
    job_url: str                         # unique identifier for deduplication
    source: str                          # e.g. "itviec", "topcv"
    location: Optional[str] = None
    posted_time: Optional[str] = None
    description: Optional[str] = None   # raw HTML or plain text from detail page
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    skills_raw: List[str] = field(default_factory=list)  # explicitly listed skills


class BaseCrawler(ABC):
    """
    Abstract crawler interface.

    Subclasses must implement:
      - fetch_job_list(page) → list of partial RawJob (no description yet)
      - fetch_job_detail(raw_job) → completed RawJob with description filled in
    """

    SOURCE_NAME: str = "unknown"

    def get_source_name(self) -> str:
        return self.SOURCE_NAME

    @abstractmethod
    def fetch_job_list(self, page: int = 1) -> List[RawJob]:
        """
        Crawl the job listing page and return a list of RawJob stubs.
        Each stub should have at minimum: job_title, company, job_url, source.
        """
        ...

    @abstractmethod
    def fetch_job_detail(self, raw_job: RawJob) -> RawJob:
        """
        Given a RawJob stub from fetch_job_list, visit job_url and fill in
        description, requirements, benefits, skills_raw fields.
        Returns the enriched RawJob.
        """
        ...
