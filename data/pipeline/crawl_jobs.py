"""
data/pipeline/crawl_jobs.py
============================
VietnamWorks Job Detail Pipeline
---------------------------------
Reads  : data/vietnamworks_jobs.csv   (jobId, title, company, jobUrl)
Writes : data/new_training_data.csv   (job_id, title, company, job_url,
                                        description, requirements, benefits,
                                        skills, raw_text)
Caches : data/pipeline/html_cache/<job_id>.html  (raw HTML per job)
Logs   : data/pipeline/crawl.log

Pipeline per job:
  fetch_html  →  parse_job  →  clean_text  →  extract_skills  →  save row

Usage:
    # Full run (all 9,950 jobs):
    python data/pipeline/crawl_jobs.py

    # Test run (first 10 jobs):
    python data/pipeline/crawl_jobs.py --limit 10

    # Resume (skip already-completed job_ids):
    python data/pipeline/crawl_jobs.py          # auto-resumes from existing output

    # Custom input/output:
    python data/pipeline/crawl_jobs.py \\
        --input  data/vietnamworks_jobs.csv \\
        --output data/new_training_data.csv \\
        --limit  100 \\
        --workers 3
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import io
import requests
from bs4 import BeautifulSoup

# ── Resolve project root so we can import skills_config regardless of cwd ─────
# ── Windows UTF-8 console fix ────────────────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except AttributeError:
        pass

_PIPELINE_DIR = Path(__file__).parent.resolve()
_PROJECT_ROOT = _PIPELINE_DIR.parent.parent  # data/pipeline → data → project
sys.path.insert(0, str(_PIPELINE_DIR))

from skills_config import SKILL_PATTERNS  # noqa: E402

# ── Paths ─────────────────────────────────────────────────────────────────────
DEFAULT_INPUT  = _PROJECT_ROOT / "data" / "vietnamworks_jobs.csv"
DEFAULT_OUTPUT = _PROJECT_ROOT / "data" / "new_training_data.csv"
HTML_CACHE_DIR = _PIPELINE_DIR / "html_cache"
LOG_FILE       = _PIPELINE_DIR / "crawl.log"

# ── HTTP config ───────────────────────────────────────────────────────────────
MAX_RETRY   = 3
TIMEOUT     = 10          # seconds per attempt
SLEEP_MIN   = 1.5         # seconds between requests per worker
SLEEP_MAX   = 3.0
BACKOFF_BASE = 2          # exponential backoff multiplier on retry

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.vietnamworks.com/",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# ── Output schema ─────────────────────────────────────────────────────────────
OUTPUT_FIELDS = [
    "job_id", "title", "company", "job_url",
    "description", "requirements", "benefits",
    "skills", "raw_text",
]


# ═══════════════════════════════════════════════════════════════════════════════
#  LOGGING SETUP
# ═══════════════════════════════════════════════════════════════════════════════

def setup_logging() -> logging.Logger:
    """Configure a logger that writes to both stderr and crawl.log."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("crawl_pipeline")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler (INFO+)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    # File handler (DEBUG+)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger


log = setup_logging()


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 1 — FETCH HTML
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_html(url: str, job_id: str) -> Optional[str]:
    """
    Fetch the raw HTML for a VietnamWorks job page.

    Features:
    - Checks HTML cache first (file: html_cache/<job_id>.html)
    - Up to MAX_RETRY attempts with exponential back-off
    - Timeout: TIMEOUT seconds per attempt
    - Returns None on permanent failure (caller will log + skip)
    """
    # ── Cache hit ──────────────────────────────────────────────────────────
    cache_path = HTML_CACHE_DIR / f"{job_id}.html"
    if cache_path.exists():
        log.debug(f"[CACHE] {job_id} — served from disk")
        return cache_path.read_text(encoding="utf-8", errors="replace")

    # ── Live fetch with retry ──────────────────────────────────────────────
    for attempt in range(1, MAX_RETRY + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code == 200:
                html = resp.text
                # Save to cache
                HTML_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(html, encoding="utf-8")
                log.debug(f"[FETCH] {job_id} — HTTP 200, {len(html):,} chars, cached")
                return html
            elif resp.status_code in (403, 429):
                wait = BACKOFF_BASE ** attempt + random.uniform(1, 3)
                log.warning(
                    f"[FETCH] {job_id} — HTTP {resp.status_code} on attempt {attempt}, "
                    f"backing off {wait:.1f}s"
                )
                time.sleep(wait)
            else:
                log.warning(f"[FETCH] {job_id} — HTTP {resp.status_code} on attempt {attempt}")
        except requests.exceptions.Timeout:
            wait = BACKOFF_BASE ** attempt
            log.warning(f"[FETCH] {job_id} — Timeout on attempt {attempt}, retry in {wait}s")
            time.sleep(wait)
        except requests.exceptions.ConnectionError as exc:
            wait = BACKOFF_BASE ** attempt
            log.warning(f"[FETCH] {job_id} — ConnectionError attempt {attempt}: {exc}, retry in {wait}s")
            time.sleep(wait)
        except requests.exceptions.RequestException as exc:
            log.error(f"[FETCH] {job_id} — Unrecoverable error: {exc}")
            return None

    log.error(f"[FETCH] {job_id} — FAILED after {MAX_RETRY} attempts")
    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 2 — RSC CHUNK PARSING  (VietnamWorks Next.js streaming format)
# ═══════════════════════════════════════════════════════════════════════════════

def _deep_merge(target: dict, source) -> None:
    """
    Recursively walk *source* (dict or list) and collect every
    key→value pair into the flat *target* dict.
    This flattens VietnamWorks' deeply nested RSC JSON tree.
    """
    if isinstance(source, dict):
        for k, v in source.items():
            target[k] = v
            if isinstance(v, (dict, list)):
                _deep_merge(target, v)
    elif isinstance(source, list):
        for item in source:
            if isinstance(item, (dict, list)):
                _deep_merge(target, item)


_CHUNK_PATTERN = re.compile(
    r'self\.__next_f\.push\(\s*(\[.*?\])\s*\)',
    re.DOTALL,
)
_RSC_PREFIX = re.compile(r'^\d+:')
# RSC "line protocol" pattern: each line is   <hex_key>:<value>
# e.g.  24:T1a3c,<html>...</html>
#       2c:["$","div",...]
_RSC_LINE = re.compile(r'^([0-9a-fA-F]+):(.*)$', re.MULTILINE)


def _parse_rsc_lines(text: str, merged: dict) -> None:
    """
    VietnamWorks uses RSC "flight" line protocol inside push() string payloads.
    Each line is   KEY:VALUE   where:
      - KEY is a hex string (e.g. "24", "2c")
      - VALUE is one of:
        * T<hexlen>,<raw_content>   — raw HTML/text blob
        * JSON string               — array or object
        * plain string

    We build a ref-table so that $ref pointers like "$24" can be resolved.
    """
    for m in _RSC_LINE.finditer(text):
        key = m.group(1)      # hex ref key
        value_raw = m.group(2).strip()

        if not value_raw:
            continue

        # Type T: raw blob  T<hexlen>,<content>
        if value_raw.startswith('T'):
            comma_idx = value_raw.find(',')
            if comma_idx >= 0:
                raw_content = value_raw[comma_idx + 1:]
                merged[key] = raw_content  # raw HTML string
            continue

        # Type I: module reference — skip
        if value_raw.startswith('I') or value_raw.startswith('HL'):
            continue

        # Try JSON
        try:
            parsed = json.loads(value_raw)
            merged[key] = parsed
            if isinstance(parsed, (dict, list)):
                _deep_merge(merged, parsed)
        except json.JSONDecodeError:
            # Plain string value
            merged[key] = value_raw


def _extract_chunks(html: str) -> dict:
    """
    Parse every  self.__next_f.push([...])  call in the page HTML,
    decode the inner JSON-encoded string payloads, and deep-merge
    all discovered key→value pairs into a single flat dict.

    VietnamWorks uses React Server Components (RSC) streaming:
    - Multiple push() calls build up the page data incrementally.
    - Payloads are either raw dicts/lists or JSON-encoded strings.
    - String payloads may carry a numeric RSC prefix like "1:" or "2:{"
    """
    merged: dict = {}

    for match in _CHUNK_PATTERN.finditer(html):
        raw_array = match.group(1)
        try:
            arr = json.loads(raw_array)
        except json.JSONDecodeError:
            continue

        if len(arr) < 2:
            continue

        payload = arr[1]

        # ── Case A: payload already decoded as dict/list ──────────────────
        if isinstance(payload, (dict, list)):
            _deep_merge(merged, payload)
            continue

        # ── Case B: payload is a JSON-encoded string ──────────────────────
        if isinstance(payload, str):
            # First: treat the whole string as RSC line-protocol
            # (handles multi-line blocks like '24:T...,<html>\n2c:[...] ')
            _parse_rsc_lines(payload, merged)

            # Then strip RSC numeric prefix and try JSON parse of the remainder
            cleaned = _RSC_PREFIX.sub("", payload.strip())

            # Try to parse as-is
            try:
                inner = json.loads(cleaned)
                if isinstance(inner, (dict, list)):
                    _deep_merge(merged, inner)
                continue
            except json.JSONDecodeError:
                pass

            # Fallback: extract the first {...} or [...] block
            obj_match = re.search(r'(\{.*\}|\[.*\])', cleaned, re.DOTALL)
            if obj_match:
                try:
                    inner = json.loads(obj_match.group(1))
                    if isinstance(inner, (dict, list)):
                        _deep_merge(merged, inner)
                except json.JSONDecodeError:
                    pass

    return merged


def _resolve_ref(value, merged: dict):
    """
    VietnamWorks uses RSC reference encoding:  "$2c" means look up "2c" in merged.
    Recurse until we reach a concrete (non-reference) value.
    Guard against infinite loops with a depth limit.
    """
    depth = 0
    while isinstance(value, str) and value.startswith("$") and depth < 20:
        ref_key = value[1:]
        resolved = merged.get(ref_key)
        if resolved is None:
            break
        value = resolved
        depth += 1
    return value


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 3 — TEXT CLEANING
# ═══════════════════════════════════════════════════════════════════════════════

_MULTI_NEWLINE = re.compile(r'\n{3,}')
_MULTI_SPACE   = re.compile(r'[ \t]+')
_CONTROL_CHARS = re.compile(r'[\r\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def _html_to_text(raw) -> str:
    """
    Convert an HTML string (or any value) to clean plain text.
    Preserves paragraph / list-item line breaks for readability.
    """
    if not raw:
        return ""
    if not isinstance(raw, str):
        raw = str(raw)

    # Add newlines before block-level closing tags so get_text preserves structure
    for tag in ("</p>", "</li>", "</div>", "<br>", "<br/>", "<br />"):
        raw = raw.replace(tag, tag + "\n")

    try:
        soup = BeautifulSoup(raw, "html.parser")
        text = soup.get_text(separator="\n")
    except Exception:
        # Last-resort: regex strip
        text = re.sub(r'<[^>]+>', ' ', raw)

    return text


def clean_text(text: str) -> str:
    """
    Normalize text:
    1. Strip/decode HTML
    2. Remove control characters
    3. Collapse multiple spaces on each line
    4. Collapse 3+ consecutive blank lines → max 2
    5. Strip leading/trailing whitespace
    6. Ensure valid UTF-8 (encode/decode round-trip)
    """
    if not text:
        return ""

    # Decode HTML entities + strip tags
    text = _html_to_text(text)

    # Remove unwanted control characters (keep \n \t)
    text = _CONTROL_CHARS.sub("", text)

    # Collapse multiple spaces/tabs within each line
    lines = [_MULTI_SPACE.sub(" ", line).strip() for line in text.splitlines()]
    text = "\n".join(lines)

    # Collapse too many blank lines
    text = _MULTI_NEWLINE.sub("\n\n", text).strip()

    # Guarantee UTF-8 (drop un-encodable chars)
    text = text.encode("utf-8", errors="ignore").decode("utf-8")

    return text


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 4 — SKILL EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_skills(text: str) -> str:
    """
    Case-insensitive keyword scan using pre-compiled patterns from skills_config.
    Returns a comma-separated string of matched skill names (canonical casing).
    """
    if not text:
        return ""
    found: set[str] = set()
    for canonical, pattern in SKILL_PATTERNS:
        if pattern.search(text):
            found.add(canonical)
    return ", ".join(sorted(found))


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 5 — PARSE ONE JOB PAGE
# ═══════════════════════════════════════════════════════════════════════════════

def parse_job(html: str) -> dict:
    """
    Extract structured job data from raw VietnamWorks HTML.

    Primary path: RSC chunk parsing (self.__next_f.push).
    Fallback: BeautifulSoup CSS selector scan on the raw HTML.

    Returns dict with keys: description, requirements, benefits.
    All values are clean plain text (empty string if section absent).
    """
    # ── Primary: RSC chunks ────────────────────────────────────────────────
    merged = _extract_chunks(html)

    def get(field: str):
        return _resolve_ref(merged.get(field), merged)

    description  = clean_text(get("jobDescription") or "")
    requirements = clean_text(get("jobRequirement") or "")
    benefits     = clean_text(get("benefits") or "")

    # ── Fallback: BeautifulSoup selectors (if RSC yielded nothing) ─────────
    if not description and not requirements:
        soup = BeautifulSoup(html, "html.parser")
        description  = _bs_extract(soup, [
            "div.job-description", "div#job-description",
            "div[class*='job-desc']", "section.description",
            "div.detail-description",
        ])
        requirements = _bs_extract(soup, [
            "div.job-requirement", "div#job-requirement",
            "div[class*='requirement']", "section.requirement",
        ])
        benefits     = _bs_extract(soup, [
            "div.welfare-item", "div[class*='benefit']",
            "div[class*='welfare']", "section.benefit",
        ])

    return {
        "description":  description,
        "requirements": requirements,
        "benefits":     benefits,
    }


def _bs_extract(soup: BeautifulSoup, selectors: list[str]) -> str:
    """Try each CSS selector in order; return clean text from the first match."""
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            return clean_text(str(el))
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
#  STEP 6 — PROCESS ONE JOB (full pipeline, thread-safe)
# ═══════════════════════════════════════════════════════════════════════════════

def process_job(row: dict) -> Optional[dict]:
    """
    Full pipeline for a single job row from the input CSV.

    Args:
        row: dict with keys jobId, title, company, jobUrl

    Returns:
        Flat output dict matching OUTPUT_FIELDS, or None on failure.
    """
    job_id  = str(row.get("jobId", "")).strip()
    title   = str(row.get("title", "")).strip()
    company = str(row.get("company", "")).strip()
    url     = str(row.get("jobUrl", "")).strip()

    if not url.startswith("http"):
        log.warning(f"[SKIP] {job_id} — invalid URL: {url!r}")
        return None

    # Polite delay ONLY when fetching live (cache hits skip the delay)
    cache_path = HTML_CACHE_DIR / f"{job_id}.html"
    if not cache_path.exists():
        time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))

    # Fetch
    html = fetch_html(url, job_id)
    if html is None:
        log.error(f"[ERROR] {job_id} failed — HTML fetch returned None")
        return None

    # Parse
    try:
        parsed = parse_job(html)
    except Exception as exc:
        log.error(f"[ERROR] {job_id} failed — parse_job raised: {exc}", exc_info=True)
        return None

    description  = parsed["description"]
    requirements = parsed["requirements"]
    benefits     = parsed["benefits"]

    raw_text = "\n\n".join(filter(None, [description, requirements, benefits]))
    skills   = extract_skills(raw_text)

    log.info(f"[CRAWL] {job_id} OK  title={title!r}  skills={skills[:60]!r}")

    return {
        "job_id":       job_id,
        "title":        title,
        "company":      company,
        "job_url":      url,
        "description":  description,
        "requirements": requirements,
        "benefits":     benefits,
        "skills":       skills,
        "raw_text":     raw_text,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  CSV helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _load_existing_ids(output_path: Path) -> set[str]:
    """Return the set of job_ids already written to the output CSV."""
    if not output_path.exists():
        return set()
    seen: set[str] = set()
    try:
        with output_path.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                jid = row.get("job_id", "").strip()
                if jid:
                    seen.add(jid)
        log.info(f"[RESUME] Found {len(seen)} already-processed jobs in {output_path.name}")
    except Exception as exc:
        log.warning(f"[RESUME] Could not read existing output: {exc}")
    return seen


def _append_rows(rows: list[dict], output_path: Path) -> None:
    """Append a batch of rows to the output CSV (create with header if new)."""
    is_new = not output_path.exists()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        if is_new:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _load_input(input_path: Path) -> list[dict]:
    """Read the input CSV into a list of dicts."""
    rows: list[dict] = []
    with input_path.open(encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="VietnamWorks Job Detail Pipeline",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input CSV path (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of jobs to process (default: all). Use --limit 10 for a test run.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Max concurrent HTTP workers (default: 3). Keep low to avoid blocking.",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=50,
        dest="checkpoint_every",
        help="Save output CSV every N completed jobs (default: 50).",
    )
    args = parser.parse_args()

    # ── Banner ────────────────────────────────────────────────────────────
    log.info("=" * 65)
    log.info("  VietnamWorks Job Detail Pipeline")
    log.info("=" * 65)
    log.info(f"  Input    : {args.input}")
    log.info(f"  Output   : {args.output}")
    log.info(f"  Workers  : {args.workers}")
    log.info(f"  Limit    : {args.limit or 'ALL'}")
    log.info(f"  HTML cache: {HTML_CACHE_DIR}")
    log.info(f"  Log file : {LOG_FILE}")
    log.info("=" * 65)

    # ── Load input ────────────────────────────────────────────────────────
    if not args.input.exists():
        log.error(f"Input file not found: {args.input}")
        sys.exit(1)

    all_rows = _load_input(args.input)
    log.info(f"Loaded {len(all_rows):,} rows from {args.input.name}")

    # ── Resume: skip already-done job_ids ─────────────────────────────────
    done_ids = _load_existing_ids(args.output)

    pending = [
        r for r in all_rows
        if str(r.get("jobId", "")).strip() not in done_ids
        and str(r.get("jobUrl", "")).strip().startswith("http")
    ]

    if args.limit:
        pending = pending[: args.limit]

    total = len(pending)
    log.info(f"Jobs to process: {total:,}  (skipping {len(done_ids):,} already done)")

    if total == 0:
        log.info("Nothing to do. Exiting.")
        return

    # ── Sequential crawl (Ctrl+C safe, cache-friendly) ────────────────────
    # NOTE: HTML already cached → sequential is fast enough & far more stable
    results:  list[dict] = []
    failures: list[str]  = []
    batch:    list[dict] = []
    interrupted = False

    start_time = time.monotonic()

    for completed, row in enumerate(pending, start=1):
        job_id = str(row.get("jobId", "")).strip()

        try:
            result = process_job(row)
        except KeyboardInterrupt:
            log.warning("\n[INTERRUPT] Ctrl+C received — saving progress and exiting...")
            interrupted = True
            break
        except Exception as exc:
            log.error(f"[ERROR] {job_id} — unexpected exception: {exc}", exc_info=True)
            result = None

        if result:
            results.append(result)
            batch.append(result)
        else:
            failures.append(job_id)

        # Progress every job
        pct = completed / total * 100
        elapsed = time.monotonic() - start_time
        rate = completed / elapsed if elapsed > 0 else 0
        eta = (total - completed) / rate if rate > 0 else 0
        log.info(
            f"  Progress: {completed}/{total} ({pct:.1f}%)  "
            f"OK:{len(results)} FAIL:{len(failures)}  "
            f"~{eta/60:.1f}min remaining"
        )

        # Checkpoint save every N jobs
        if len(batch) >= args.checkpoint_every:
            _append_rows(batch, args.output)
            log.info(f"  [CHECKPOINT] Saved {len(batch)} rows -> {args.output.name}")
            batch.clear()

    # Final flush (always save remaining batch)
    if batch:
        _append_rows(batch, args.output)
        log.info(f"  [FLUSH] Saved {len(batch)} remaining rows -> {args.output.name}")

    # ── Summary ───────────────────────────────────────────────────────────
    elapsed = time.monotonic() - start_time
    log.info("")
    log.info("=" * 65)
    if interrupted:
        log.info("  INTERRUPTED — partial results saved (re-run to resume)")
    else:
        log.info(f"  DONE in {elapsed:.1f}s")
    log.info(f"  Succeeded : {len(results):,}")
    log.info(f"  Failed    : {len(failures):,}")
    log.info(f"  Output    : {args.output}")
    log.info("=" * 65)

    if failures:
        failed_log = _PIPELINE_DIR / "failed_urls.txt"
        failed_log.write_text("\n".join(failures), encoding="utf-8")
        log.warning(f"  Failed job IDs written to: {failed_log}")


if __name__ == "__main__":
    main()
