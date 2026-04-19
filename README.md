# JobMatch AI — Job Recommendation System v2.0

> **SBERT-powered job recommendation with multi-source crawling, real-time matching, and monitoring dashboard**

## 🏗️ Architecture

```
React (Vite + TailwindCSS)  →  FastAPI  →  PostgreSQL + pgvector
                                  ↕
                          Sentence-BERT + Continual Learning
                                  ↕
                 APScheduler → [ITviec | TopCV | VietnamWorks] Crawlers
                                  ↓
                        Real-time CV→Job Matching Trigger
```

## 🚀 Quick Start

### Prerequisites
- Docker Desktop (required for PostgreSQL + pgvector)

### 1. Start everything with Docker Compose

```bash
docker-compose up --build
```

This starts:
- `db` — PostgreSQL 16 + pgvector on port 5432
- `backend` — FastAPI on http://localhost:8000
- `frontend` — React on http://localhost:5173

> **Note:** First build takes ~5-10 min (downloads SBERT model ~90MB). Subsequent starts are fast.

### 2. Access the app

| Service | URL |
|---|---|
| **Frontend** | http://localhost:5173 |
| **API Docs (Swagger)** | http://localhost:8000/api/docs |
| **Health Check** | http://localhost:8000/health |
| **Crawler Stats** | http://localhost:8000/api/v1/crawler/stats |
| **Crawler Logs** | http://localhost:8000/api/v1/crawler/logs |

---

## 💻 Local Development (without Docker)

### Backend

```bash
# 1. Create virtualenv
python -m venv venv
venv\Scripts\activate      # Windows

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Copy .env
copy backend\.env.example backend\.env

# 4. Start PostgreSQL via Docker (required for pgvector)
docker-compose up -d db

# 5. Run FastAPI
cd backend
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # Starts on http://localhost:5173
```

---

## 🕷️ Running Crawlers Manually

```bash
cd backend

# Crawl all sources (ITviec + TopCV + VietnamWorks)
python -m crawler.main --source all --pages 1

# Crawl a specific source
python -m crawler.main --source itviec --pages 2
python -m crawler.main --source topcv --pages 1
python -m crawler.main --source vietnamworks --pages 1

# Skip embedding generation (faster for testing)
python -m crawler.main --source all --pages 1 --no-embed
```

**Automated crawling** runs every 10 minutes via APScheduler (starts with FastAPI):
- VietnamWorks starts 6 minutes after ITviec

---

## 📁 Project Structure

```
cv-job-recommendation-system/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI entry point + scheduler registration
│   │   ├── config.py              # Settings
│   │   ├── database.py            # SQLAlchemy async
│   │   ├── models/                # ORM: User, CV, Job, Interaction, CrawlLog
│   │   ├── schemas/               # Pydantic schemas
│   │   ├── routers/               # auth, cvs, jobs, recommend, analytics, crawler
│   │   ├── services/              # auth, cv_parser, embedding, recommendation, continual_learning
│   │   │                          # + recommendation_trigger (real-time matching)
│   │   └── ml/                    # preprocessing, sbert_model, trainer, recommender
│   ├── crawler/
│   │   ├── base_crawler.py        # Abstract base class + RawJob dataclass
│   │   ├── itviec_crawler.py      # ITviec scraper
│   │   ├── topcv_crawler.py       # TopCV scraper (NEW)
│   │   ├── vietnamworks_crawler.py# VietnamWorks scraper (NEW)
│   │   ├── pipeline.py            # Crawl → clean → embed → upsert pipeline
│   │   ├── scheduler.py           # APScheduler job registration (3 sources)
│   │   ├── main.py                # CLI entry point (--source all/itviec/topcv/...)
│   │   ├── alerts.py              # Telegram/console alert system (NEW)
│   │   ├── database.py            # upsert_job + dedup helpers
│   │   ├── config.py              # Crawler env settings
│   │   └── utils.py               # HTTP session, HTML cleaning, skill extraction
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── pages/                 # Login, Register, Dashboard, Upload, Recommend, Analytics
│   │   ├── components/layout/     # Navbar, PublicLayout
│   │   ├── api/                   # axios clients for all endpoints
│   │   └── store/                 # Zustand auth store
│   ├── Dockerfile
│   └── package.json
│
├── data/
│   └── training_data.csv          # Seed data (auto-loaded on startup)
├── docker-compose.yml
└── README.md
```

---

## 🤖 Key Features

### 1. Multi-Source Crawler (NEW)
- **VietnamWorks** — HTML + JSON-LD dual parsing strategy
- Deduplication by URL, retry with exponential backoff, polite delays

### 2. Real-time Job-to-CV Matching (NEW)
- When a new job is inserted → automatically computes cosine similarity vs all CV embeddings
- Top matches (score ≥ 0.40) saved as `UserInteraction` records immediately
- Users see newly crawled jobs in their recommendations without any action

### 3. Crawler Monitoring (NEW)
- `GET /api/v1/crawler/stats` — per-source: jobs today, errors, last run time, status
- `GET /api/v1/crawler/logs` — 50 most recent crawl log entries
- `GET /api/v1/crawler/trend` — daily jobs per source (last 7 days)
- Structured JSON logs emitted for every crawl event

### 4. Alert System (NEW)
- Detects HTTP 403 blocks and high error rates (>50%)
- Sends Telegram message if `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` are configured
- Falls back to console log if not configured

### 5. Sentence-BERT Recommendations
- Uses `all-MiniLM-L6-v2` (384-dim embeddings, fast CPU inference)
- pgvector `<=>` cosine distance operator for fast vector search
- Recommend by uploaded CV or by job title

### 6. Continual Learning
- Users rate jobs: ✅ Applied / 🔖 Saved / ✕ Skipped
- After `RETRAIN_THRESHOLD` interactions → background fine-tuning
- EWC (Elastic Weight Consolidation) + Replay Buffer to prevent catastrophic forgetting
- Auto-rollback if new model performs >5% worse

---

## 🔧 Environment Variables

```bash
# backend/.env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost/jobrec
SECRET_KEY=change-this-to-a-random-secret-key-min-32-chars
RETRAIN_THRESHOLD=100       # Lower to 5 for testing continual learning

# Crawler
CRAWLER_INTERVAL_MINUTES=10
CRAWLER_MAX_JOBS_PER_RUN=30
CRAWLER_PAGES_PER_RUN=2
CRAWLER_EMBED_ON_INSERT=true

# Alerts (optional — leave empty to use console-only)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

---

## 🛠️ API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register user |
| POST | `/api/v1/auth/login` | Login → JWT |
| POST | `/api/v1/cvs/upload` | Upload PDF/DOCX CV |
| GET | `/api/v1/cvs` | List user's CVs |
| POST | `/api/v1/recommend/by-cv` | Recommend jobs by CV |
| POST | `/api/v1/recommend/by-title` | Recommend by job title |
| POST | `/api/v1/recommend/feedback` | Rate a recommendation |
| GET | `/api/v1/analytics/stats` | Dashboard stats |
| GET | `/api/v1/jobs` | List all jobs |
| GET | `/api/v1/crawler/stats` | **Crawler monitoring stats** |
| GET | `/api/v1/crawler/logs` | **Recent crawl logs** |
| GET | `/api/v1/crawler/logs/{source}` | **Logs for specific source** |
| GET | `/api/v1/crawler/trend` | **Jobs per day chart data** |

---

*Built with FastAPI + Sentence-BERT + pgvector + React + TailwindCSS + BeautifulSoup*
