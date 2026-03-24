# JobMatch AI — Job Recommendation System v2.0

> **SBERT-powered job recommendation with Continual Learning, FastAPI backend, and React frontend**

## 🏗️ Architecture

```
React (Vite + TailwindCSS)  →  FastAPI  →  PostgreSQL + pgvector
                                  ↕
                          Sentence-BERT + Continual Learning
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

---

## 💻 Local Development (without Docker)

### Backend

```bash
# 1. Create conda/venv
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

## 📁 Project Structure

```
cv-job-recommendation-system/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI entry point
│   │   ├── config.py              # Settings
│   │   ├── database.py            # SQLAlchemy async
│   │   ├── models/                # ORM: User, CV, Job, Interaction
│   │   ├── schemas/               # Pydantic schemas
│   │   ├── routers/               # auth, cvs, jobs, recommend, analytics
│   │   ├── services/              # auth, cv_parser, embedding, recommendation, continual_learning
│   │   └── ml/                    # preprocessing, sbert_model, trainer, recommender
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── pages/                 # Login, Register, Dashboard, Upload, Recommend, Analytics
│   │   ├── components/layout/     # Sidebar, Navbar, PageLayout
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

### 1. Sentence-BERT Recommendations
- Uses `all-MiniLM-L6-v2` (384-dim embeddings, fast CPU inference)
- pgvector `<=>` cosine distance operator for fast vector search
- Recommend by uploaded CV or by job title

### 2. Continual Learning
- Users rate jobs: ✅ Applied / 🔖 Saved / ✕ Skipped
- After `RETRAIN_THRESHOLD` interactions → background fine-tuning
- EWC (Elastic Weight Consolidation) + Replay Buffer to prevent catastrophic forgetting
- Auto-rollback if new model performs >5% worse

### 3. Analytics Dashboard
- Similarity score distribution histogram
- Top matched jobs bar chart
- 7-day activity line chart
- Applied/Saved/Skipped pie chart

---

## 🔧 Environment Variables

```bash
# backend/.env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost/jobrec
SECRET_KEY=change-this-to-a-random-secret-key-min-32-chars
RETRAIN_THRESHOLD=100   # Lower to 5 for testing continual learning
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

---

*Built with FastAPI + Sentence-BERT + pgvector + React + TailwindCSS*
