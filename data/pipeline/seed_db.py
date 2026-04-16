"""
data/pipeline/seed_db.py
==========================
Seeds the PostgreSQL (pgvector) database from new_training_data.csv.

What it does:
  1. Reads data/new_training_data.csv (output of crawl_jobs.py)
  2. For each row, generates an SBERT embedding via the app's embedding service
  3. Upserts the job into the job_descriptions table:
       - INSERT if the job_url (link) is new
       - UPDATE description/skills/embedding if it already exists
  4. Commits in batches of BATCH_SIZE

Requirements:
  - PostgreSQL running with pgvector enabled
  - DATABASE_URL set in backend/.env (or as env var)
  - sentence-transformers installed

Usage (from project root):
    # With default paths:
    python data/pipeline/seed_db.py

    # Custom CSV + env file:
    python data/pipeline/seed_db.py \\
        --csv   data/new_training_data.csv \\
        --env   backend/.env \\
        --batch 100 \\
        --limit 500

    # Dry-run (parse rows, no DB writes):
    python data/pipeline/seed_db.py --dry-run
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

# ── Project root on path ─────────────────────────────────────────────────────
_PIPELINE_DIR  = Path(__file__).parent.resolve()
_PROJECT_ROOT  = _PIPELINE_DIR.parent.parent
_BACKEND_DIR   = _PROJECT_ROOT / "backend"

sys.path.insert(0, str(_BACKEND_DIR))

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_CSV     = _PROJECT_ROOT / "data" / "new_training_data.csv"
DEFAULT_ENV     = _BACKEND_DIR / ".env"
DEFAULT_BATCH   = 50
SEED_LOG_FILE   = _PIPELINE_DIR / "seed_db.log"


# ═══════════════════════════════════════════════════════════════════════════════
#  LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

def setup_logging() -> logging.Logger:
    SEED_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("seed_db")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    fh = logging.FileHandler(SEED_LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger


log = setup_logging()


# ═══════════════════════════════════════════════════════════════════════════════
#  LOAD ENV
# ═══════════════════════════════════════════════════════════════════════════════

def load_env(env_path: Path) -> None:
    """Load .env file into os.environ using python-dotenv (if available)."""
    if not env_path.exists():
        log.warning(f"[ENV] .env file not found: {env_path} — relying on OS env vars")
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
        log.info(f"[ENV] Loaded {env_path}")
    except ImportError:
        # Manual parse — basic KEY=VALUE only
        log.warning("[ENV] python-dotenv not installed — parsing .env manually")
        with env_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)


# ═══════════════════════════════════════════════════════════════════════════════
#  CSV READER
# ═══════════════════════════════════════════════════════════════════════════════

def load_csv(csv_path: Path, limit: Optional[int] = None) -> list[dict]:
    """Read new_training_data.csv into a list of dicts."""
    if not csv_path.exists():
        log.error(f"[CSV] File not found: {csv_path}")
        sys.exit(1)

    rows: list[dict] = []
    with csv_path.open(encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
            if limit and len(rows) >= limit:
                break

    log.info(f"[CSV] Loaded {len(rows):,} rows from {csv_path.name}")
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
#  EMBEDDING
# ═══════════════════════════════════════════════════════════════════════════════

def _load_embedding_model():
    """
    Load SBERT model for embedding.
    Tries to reuse app's embedding_service first; falls back to raw sentence-transformers.
    """
    model_name = os.environ.get("SBERT_MODEL_NAME", "all-MiniLM-L6-v2")
    try:
        from app.services.embedding_service import embedding_service
        log.info(f"[EMBED] Using app embedding_service (model: {model_name})")
        return embedding_service
    except Exception:
        pass

    try:
        from sentence_transformers import SentenceTransformer

        class _FallbackService:
            def __init__(self):
                log.info(f"[EMBED] Loading SentenceTransformer({model_name!r}) directly")
                self._model = SentenceTransformer(model_name)

            def encode(self, text: str):
                return self._model.encode(text, normalize_embeddings=True)

            def encode_batch(self, texts: list[str], batch_size: int = 32):
                return self._model.encode(
                    texts,
                    batch_size=batch_size,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )

        return _FallbackService()
    except ImportError:
        log.warning("[EMBED] sentence-transformers not installed — embeddings will be NULL")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  DB UPSERT (synchronous psycopg2 for standalone script)
# ═══════════════════════════════════════════════════════════════════════════════

UPSERT_SQL = """
INSERT INTO job_descriptions (
    id, position_title, company, description, cleaned_description,
    link, skills, source, is_active, embedding
)
VALUES (
    %(id)s, %(position_title)s, %(company)s, %(description)s, %(cleaned_description)s,
    %(link)s, %(skills)s, %(source)s, %(is_active)s,
    %(embedding)s::vector
)
ON CONFLICT (link)
DO UPDATE SET
    position_title      = EXCLUDED.position_title,
    company             = EXCLUDED.company,
    description         = EXCLUDED.description,
    cleaned_description = EXCLUDED.cleaned_description,
    skills              = EXCLUDED.skills,
    embedding           = EXCLUDED.embedding,
    updated_at          = now()
"""


def _build_db_url_sync(async_url: str) -> str:
    """Convert asyncpg DATABASE_URL to a psycopg2-compatible URL."""
    return (
        async_url
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
    )


def connect_db(database_url: str):
    """Return a psycopg2 connection, or raise on failure."""
    sync_url = _build_db_url_sync(database_url)
    try:
        import psycopg2
        from psycopg2.extras import register_uuid
        conn = psycopg2.connect(sync_url)
        register_uuid()
        log.info("[DB] Connected to PostgreSQL")
        return conn
    except ImportError:
        log.error("[DB] psycopg2 not installed. Run: pip install psycopg2-binary")
        sys.exit(1)
    except Exception as exc:
        log.error(f"[DB] Connection failed: {exc}")
        sys.exit(1)


def _prepare_skills(skills_str: str) -> Optional[list]:
    """Convert comma-separated skills string to PostgreSQL ARRAY."""
    if not skills_str or not skills_str.strip():
        return None
    return [s.strip() for s in skills_str.split(",") if s.strip()]


def _prepare_embedding(emb) -> Optional[str]:
    """Convert numpy array / list to PostgreSQL vector literal string."""
    if emb is None:
        return None
    try:
        arr = list(emb)
        return "[" + ",".join(f"{v:.8f}" for v in arr) + "]"
    except Exception:
        return None


def upsert_batch(
    conn,
    rows: list[dict],
    embed_service,
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Upsert a batch of rows into job_descriptions.

    Returns (inserted_or_updated, errors).
    """
    upserted = 0
    errors   = 0

    # Generate embeddings for the whole batch in one shot (much faster)
    raw_texts = [r.get("raw_text", "") or "" for r in rows]
    embeddings: list = [None] * len(rows)

    if embed_service and any(raw_texts):
        try:
            emb_array = embed_service.encode_batch(raw_texts, batch_size=32)
            embeddings = list(emb_array)
        except Exception as exc:
            log.warning(f"[EMBED] Batch encode failed: {exc} — embeddings will be NULL")

    cur = conn.cursor() if not dry_run else None

    for i, row in enumerate(rows):
        link = row.get("job_url", "").strip()
        if not link:
            log.debug(f"[SKIP] Row {i} — no job_url")
            errors += 1
            continue

        # Build cleaned_description (concatenate all text sections)
        raw_text = row.get("raw_text", "") or ""
        # Apply same clean_text logic for DB field
        cleaned = raw_text.strip()

        emb_str = _prepare_embedding(embeddings[i])

        params = {
            "id":                  uuid.uuid4(),
            "position_title":      (row.get("title") or "Unknown")[:255],
            "company":             (row.get("company") or "Unknown")[:255],
            "description":         row.get("description") or raw_text or "",
            "cleaned_description": cleaned,
            "link":                link,
            "skills":              _prepare_skills(row.get("skills", "")),
            "source":              "vietnamworks",
            "is_active":           True,
            "embedding":           emb_str,
        }

        if dry_run:
            log.info(f"[DRY-RUN] Would upsert: {params['position_title']!r} @ {link[:60]}")
            upserted += 1
            continue

        try:
            cur.execute(UPSERT_SQL, params)
            upserted += 1
        except Exception as exc:
            log.error(f"[DB] Upsert failed for {link[:60]}: {exc}")
            conn.rollback()
            errors += 1
            # Re-open cursor after rollback
            cur = conn.cursor()

    if not dry_run and cur:
        try:
            conn.commit()
        except Exception as exc:
            log.error(f"[DB] Commit failed: {exc}")
            conn.rollback()
        cur.close()

    return upserted, errors


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed PostgreSQL DB from new_training_data.csv",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--csv",     type=Path, default=DEFAULT_CSV,
                        help=f"Path to new_training_data.csv (default: {DEFAULT_CSV})")
    parser.add_argument("--env",     type=Path, default=DEFAULT_ENV,
                        help=f"Path to .env file (default: {DEFAULT_ENV})")
    parser.add_argument("--batch",   type=int, default=DEFAULT_BATCH,
                        help=f"DB commit batch size (default: {DEFAULT_BATCH})")
    parser.add_argument("--limit",   type=int, default=None,
                        help="Max rows to seed (default: all)")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="Parse and log rows without writing to DB")
    args = parser.parse_args()

    # ── Banner ─────────────────────────────────────────────────────────────
    log.info("=" * 65)
    log.info("  VietnamWorks → PostgreSQL Seeder")
    log.info("=" * 65)
    log.info(f"  CSV      : {args.csv}")
    log.info(f"  Env      : {args.env}")
    log.info(f"  Batch    : {args.batch}")
    log.info(f"  Limit    : {args.limit or 'ALL'}")
    log.info(f"  Dry-run  : {args.dry_run}")
    log.info("=" * 65)

    # ── Load env ───────────────────────────────────────────────────────────
    load_env(args.env)
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        log.error("[ENV] DATABASE_URL not set. Set it in backend/.env or as env var.")
        sys.exit(1)
    log.info(f"[ENV] DATABASE_URL = {database_url[:40]}...")

    # ── Load CSV ───────────────────────────────────────────────────────────
    rows = load_csv(args.csv, limit=args.limit)
    if not rows:
        log.info("No rows to seed. Exiting.")
        return

    # ── Embedding model ────────────────────────────────────────────────────
    embed_service = _load_embedding_model()

    # ── DB connection ──────────────────────────────────────────────────────
    conn = None if args.dry_run else connect_db(database_url)

    # ── Batch upsert ───────────────────────────────────────────────────────
    total_upserted = 0
    total_errors   = 0
    start = time.monotonic()

    for batch_start in range(0, len(rows), args.batch):
        batch = rows[batch_start: batch_start + args.batch]
        batch_num = batch_start // args.batch + 1
        log.info(
            f"[BATCH {batch_num}] Processing rows "
            f"{batch_start + 1}–{batch_start + len(batch)} / {len(rows)}"
        )

        up, err = upsert_batch(conn, batch, embed_service, dry_run=args.dry_run)
        total_upserted += up
        total_errors   += err

        pct = (batch_start + len(batch)) / len(rows) * 100
        log.info(
            f"  ✓ {total_upserted} upserted  ✗ {total_errors} errors  "
            f"({pct:.1f}%)"
        )

    # ── Cleanup ────────────────────────────────────────────────────────────
    if conn:
        conn.close()

    elapsed = time.monotonic() - start
    log.info("")
    log.info("=" * 65)
    log.info(f"  DONE in {elapsed:.1f}s")
    log.info(f"  Upserted : {total_upserted:,}")
    log.info(f"  Errors   : {total_errors:,}")
    log.info("=" * 65)


if __name__ == "__main__":
    main()
