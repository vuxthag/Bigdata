# Data Pipeline

This directory contains the full data pipeline for generating `new_training_data.csv` from VietnamWorks job URLs.

## Files

| File | Purpose |
|---|---|
| `crawl_jobs.py` | Main pipeline: fetch → parse → clean → extract skills → CSV |
| `skills_config.py` | Centralised skill keyword list (edit to add/remove skills) |
| `seed_db.py` | Seed PostgreSQL/pgvector DB from the output CSV |
| `html_cache/` | Per-job raw HTML cache (auto-created, `<job_id>.html`) |
| `crawl.log` | Full crawl log (auto-created) |
| `seed_db.log` | Seeder log (auto-created) |
| `failed_urls.txt` | Job IDs that failed after all retries (auto-created if any failures) |

---

## Prerequisites

```bash
pip install requests beautifulsoup4 pandas lxml
# For seed_db.py:
pip install psycopg2-binary sentence-transformers python-dotenv
```

---

## Usage

### Step 1 — Test crawl (10 jobs)

Run from the **project root**:

```bash
python data/pipeline/crawl_jobs.py --limit 10
```

Expected output:
```
[CRAWL] 12345 ✓  title='Senior Python Developer'  skills='Docker, Python, SQL'
[CRAWL] 12346 ✓  title='React Frontend Engineer'  skills='CSS, HTML, React'
...
Progress: 10/10 (100.0%)  ✓9 ✗1  ~0.0min remaining
```

### Step 2 — Full crawl (~9,950 jobs)

```bash
python data/pipeline/crawl_jobs.py
```

- Saves progress every 50 jobs (checkpoint)
- Resumes automatically if interrupted (skips already-saved job_ids)
- Raw HTML cached to `data/pipeline/html_cache/<job_id>.html`

### Step 3 — Seed the database

```bash
# Dry-run first:
python data/pipeline/seed_db.py --dry-run --limit 20

# Full seed:
python data/pipeline/seed_db.py
```

---

## Output Schema (`new_training_data.csv`)

| Column | Description |
|---|---|
| `job_id` | VietnamWorks job ID |
| `title` | Job title |
| `company` | Company name |
| `job_url` | Original page URL |
| `description` | Job description (plain text) |
| `requirements` | Job requirements (plain text) |
| `benefits` | Benefits / perks (plain text) |
| `skills` | Comma-separated extracted skills |
| `raw_text` | description + requirements + benefits |

---

## Configuration

### Skills list
Edit `skills_config.py` — add/remove skills from `SKILLS_LIST`. No changes needed in `crawl_jobs.py`.

### Crawl speed / concurrency
Pass CLI flags:
```bash
python data/pipeline/crawl_jobs.py --workers 2 --limit 500
```

| Flag | Default | Description |
|---|---|---|
| `--workers` | 3 | Concurrent HTTP workers |
| `--limit` | all | Max jobs to process |
| `--checkpoint-every` | 50 | Save CSV every N jobs |
| `--input` | `data/vietnamworks_jobs.csv` | Input CSV |
| `--output` | `data/new_training_data.csv` | Output CSV |

---

## How VietnamWorks Parsing Works

VietnamWorks is built on **Next.js with React Server Components (RSC) streaming**. The job data is **not in visible HTML** — it's embedded in multiple JavaScript calls:

```html
<script>
self.__next_f.push([1, "{\"jobTitle\":\"...\", \"jobDescription\":\"...\"}"])
self.__next_f.push([1, "{\"jobRequirement\":\"...\"}"])
</script>
```

The parser:
1. Finds all `self.__next_f.push(...)` calls via regex
2. Decodes each JSON payload (strips RSC prefix like `"1:"`)
3. Deep-merges all key→value pairs into a flat dict
4. Resolves `$ref` pointers (e.g. `"$2c"` → look up key `"2c"`)
5. Extracts `jobDescription`, `jobRequirement`, `benefits`
6. Falls back to CSS selector scraping if RSC extraction fails

---

## Integration with Backend

After running `seed_db.py`, the `job_descriptions` PostgreSQL table will contain:
- `description` — raw text
- `cleaned_description` — normalized text for SBERT
- `embedding` — 384-dim pgvector for cosine similarity search
- `skills` — PostgreSQL ARRAY for filtering

The **recommendation engine** (`services/recommendation_service.py`) uses these fields directly — no other changes needed.

### Update `SEED_DATA_PATH` in backend config

In `backend/app/config.py`, the `SEED_DATA_PATH` setting should be updated:

```python
SEED_DATA_PATH: str = "data/new_training_data.csv"
```
