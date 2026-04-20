# CV Job Recommendation System

Hệ thống gợi ý việc làm thông minh dựa trên AI — phân tích CV và đề xuất công việc phù hợp nhất.

## Tổng quan

Ứng dụng cho phép người dùng tải lên CV (PDF/DOCX), hệ thống tự động phân tích hồ sơ, trích xuất kỹ năng, kinh nghiệm, học vấn rồi gợi ý các công việc phù hợp từ cơ sở dữ liệu (9000+ tin tuyển dụng từ VietnamWorks).

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite, TailwindCSS, shadcn/ui, Zustand |
| **Backend** | FastAPI, SQLAlchemy (async), Alembic |
| **Database** | PostgreSQL 16 + pgvector |
| **AI / ML** | Sentence-BERT (`all-MiniLM-L6-v2`), cosine similarity |
| **Crawler** | BeautifulSoup, httpx, APScheduler |
| **Auth** | JWT (python-jose) |
| **Infra** | Docker, Docker Compose |

## Kiến trúc

```
React (Vite)  ──►  FastAPI  ──►  PostgreSQL + pgvector
                      │
              Sentence-BERT (SBERT)
                      │
         ┌────────────┴────────────┐
     CV Analyzer              Job Ranker
   (skills, YOE,           (cosine sim +
    education,             skill overlap +
    job level)             YOE + level match)
                      │
              VietnamWorks Crawler
              (APScheduler, 10 min)
```

## Tính năng chính

- **Phân tích CV** — trích xuất 500+ kỹ năng công nghệ & thiết kế, kinh nghiệm, học vấn, cấp bậc
- **Gợi ý việc làm** — ranking đa tín hiệu: cosine similarity + skill overlap + YOE + job level + education
- **Tìm kiếm việc làm** — hybrid search (full-text + semantic)
- **Crawler tự động** — crawl VietnamWorks mỗi 10 phút, tạo embedding tự động
- **Dashboard** — thống kê CV, việc làm, lịch sử tương tác
- **Continual Learning** — fine-tune model dựa trên feedback người dùng

## Cài đặt nhanh

### Yêu cầu

- [Docker Desktop](https://www.docker.com/products/docker-desktop)

### Khởi động

```bash
git clone <repo-url>
cd cv-job-recommendation-system

# Copy env file
copy backend\.env.example backend\.env

# Build và chạy toàn bộ stack
docker compose up --build
```

> Lần đầu build mất ~5-10 phút (tải SBERT model ~90MB). Các lần sau khởi động nhanh.

### Truy cập

| Service | URL |
|---|---|
| **Frontend** | http://localhost:5173 |
| **API Docs** | http://localhost:8000/api/docs |
| **Health** | http://localhost:8000/health |

### Tài khoản demo

Đăng ký tài khoản mới tại `/register`. Dữ liệu việc làm được seed tự động khi khởi động.

## Cấu trúc project

```
cv-job-recommendation-system/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + lifespan (seed, scheduler)
│   │   ├── config.py            # Settings (env vars)
│   │   ├── database.py          # SQLAlchemy async session
│   │   ├── models/              # ORM: User, CV, Job, UserInteraction, CrawlLog
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── routers/             # auth, cvs, jobs, recommend, analytics, crawler
│   │   ├── services/            # cv_parser, cv_analyzer, ranking_service,
│   │   │                        # embedding_service, recommendation_service,
│   │   │                        # continual_learning, recommendation_trigger
│   │   └── ml/                  # feature_engine, preprocessing, sbert_model, trainer
│   ├── crawler/
│   │   ├── vietnamworks_crawler.py  # VietnamWorks scraper
│   │   ├── pipeline.py              # Crawl → clean → embed → upsert
│   │   ├── scheduler.py             # APScheduler registration
│   │   └── database.py              # Upsert + dedup helpers
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Unit tests
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── pages/               # Dashboard, RecommendPage, JobsPage, ProfilePage...
│   │   ├── components/          # Layout, features/dashboard, ui
│   │   ├── api/                 # axios clients: auth, cvs, jobs, recommend, analytics
│   │   └── store/               # Zustand auth store
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
│
├── data/
│   ├── jobs_full_all.csv        # Seed data ~9000 jobs từ VietnamWorks
│   └── pipeline/                # Scripts crawl & seed dữ liệu ban đầu
│
├── notebooks/                   # EDA & model exploration
├── docker-compose.yml
└── .gitignore
```

## API Endpoints chính

| Method | Endpoint | Mô tả |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Đăng ký |
| `POST` | `/api/v1/auth/login` | Đăng nhập → JWT |
| `POST` | `/api/v1/cvs/upload` | Upload CV (PDF/DOCX) |
| `GET` | `/api/v1/cvs` | Danh sách CV của user |
| `POST` | `/api/v1/recommend/cv-analysis` | **Phân tích CV + gợi ý việc làm** |
| `POST` | `/api/v1/recommend/by-cv/{cv_id}` | Gợi ý việc làm theo CV |
| `POST` | `/api/v1/recommend/feedback` | Đánh giá gợi ý |
| `GET` | `/api/v1/jobs` | Tìm kiếm việc làm |
| `POST` | `/api/v1/jobs/admin/regenerate-embeddings` | Tạo lại embeddings |
| `GET` | `/api/v1/analytics/stats` | Thống kê dashboard |
| `GET` | `/api/v1/crawler/stats` | Trạng thái crawler |

## Biến môi trường

Xem `backend/.env.example` để biết tất cả biến môi trường. Các biến quan trọng:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/jobrec
SECRET_KEY=<random-string-min-32-chars>
SEED_DATA_PATH=/app/data/jobs_full_all.csv

# Crawler
CRAWLER_INTERVAL_MINUTES=10
CRAWLER_EMBED_ON_INSERT=true

# Telegram alerts (tuỳ chọn)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

## Development không dùng Docker

```bash
# Backend
python -m venv venv
venv\Scripts\activate
pip install -r backend/requirements.txt
copy backend\.env.example backend\.env
docker compose up -d db   # Chỉ cần PostgreSQL
cd backend
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

---

*FastAPI · Sentence-BERT · pgvector · React · TailwindCSS · Docker*
