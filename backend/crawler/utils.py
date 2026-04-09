"""
crawler/utils.py
================
Shared utilities:
  - HTTP session factory with retry + User-Agent rotation
  - HTML cleaning
  - Skills keyword extractor
"""
from __future__ import annotations

import logging
import re
from typing import List

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from crawler.config import crawler_settings

logger = logging.getLogger(__name__)

# ── User-Agent pool ───────────────────────────────────────────────────────────
_USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

_ua_index = 0


def _next_user_agent() -> str:
    global _ua_index
    ua = _USER_AGENTS[_ua_index % len(_USER_AGENTS)]
    _ua_index += 1
    return ua


# ── Session factory ───────────────────────────────────────────────────────────
def build_session() -> requests.Session:
    """
    Build a requests.Session with:
    - Retry adapter (max_retries, backoff)
    - Rotating User-Agent header
    - Realistic browser headers
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=crawler_settings.CRAWLER_MAX_RETRIES,
        backoff_factor=crawler_settings.CRAWLER_BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({
        "User-Agent": _next_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    })
    return session


# ── HTML cleaning ─────────────────────────────────────────────────────────────
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def clean_html(raw: str) -> str:
    """
    Remove HTML tags and normalize whitespace.
    Uses BeautifulSoup for robustness, then normalizes.
    """
    if not raw:
        return ""
    try:
        text = BeautifulSoup(raw, "lxml").get_text(separator=" ")
    except Exception:
        # Fallback: regex strip
        text = _TAG_RE.sub(" ", raw)

    # Normalize whitespace
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


# ── Skills extractor ──────────────────────────────────────────────────────────
# Curated list of tech skills — extend as needed
_SKILLS_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b" + re.escape(skill) + r"\b", re.IGNORECASE)
    for skill in [
        # Languages
        "Python", "Java", "JavaScript", "TypeScript", "Go", "Golang",
        "Kotlin", "Swift", "Ruby", "PHP", "C++", "C#", "Rust", "Scala",
        "R", "Bash", "Shell",
        # Web Frontend
        "React", "ReactJS", "Vue", "VueJS", "Angular", "Next.js", "Nuxt",
        "HTML", "CSS", "SCSS", "Tailwind", "Bootstrap",
        # Web Backend / Frameworks
        "FastAPI", "Django", "Flask", "Express", "Spring Boot", "Laravel",
        "Node.js", "NestJS", "Rails",
        # Databases
        "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
        "SQLite", "DynamoDB", "Cassandra",
        # Data / ML / AI
        "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
        "TensorFlow", "PyTorch", "Keras", "scikit-learn", "Pandas", "NumPy",
        "Spark", "Hadoop", "Kafka", "Airflow", "dbt",
        # Cloud & DevOps
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform",
        "CI/CD", "Jenkins", "GitHub Actions", "Ansible",
        # Tools
        "Git", "Linux", "Nginx", "GraphQL", "REST", "gRPC", "Microservices",
        # Soft keywords
        "Agile", "Scrum",
    ]
]


def extract_skills(text: str) -> List[str]:
    """
    Extract skills found in text via keyword matching.
    Returns a deduplicated, sorted list.
    """
    if not text:
        return []

    found: set[str] = set()
    for pattern in _SKILLS_PATTERNS:
        match = pattern.search(text)
        if match:
            # Normalize to the canonical casing from the pattern source
            found.add(match.group())

    return sorted(found)
