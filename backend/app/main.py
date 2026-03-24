"""
main.py
=======
FastAPI application entry point.
- CORS middleware for React dev server
- All routers under /api/v1
- Startup: init DB, warm-up SBERT, seed CSV data, start APScheduler
"""
from __future__ import annotations

import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import AsyncSessionLocal, init_db
from app.routers import analytics, auth, cvs, jobs, recommend, users

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Job Recommendation API",
    description="SBERT-powered job recommendation with continual learning",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://frontend"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(auth.router, prefix=PREFIX)
app.include_router(users.router, prefix=PREFIX)
app.include_router(cvs.router, prefix=PREFIX)
app.include_router(jobs.router, prefix=PREFIX)
app.include_router(recommend.router, prefix=PREFIX)
app.include_router(analytics.router, prefix=PREFIX)

# ── Scheduler ─────────────────────────────────────────────────────────────────
scheduler = AsyncIOScheduler()


async def _check_and_retrain():
    """APScheduler job: check threshold and trigger retraining."""
    from app.services.continual_learning import continual_learner

    async with AsyncSessionLocal() as db:
        if await continual_learner.should_retrain(db):
            logger.info("[Scheduler] Retrain threshold reached — starting CL cycle...")
            result = await continual_learner.retrain(db)
            logger.info(f"[Scheduler] CL result: {result}")
        else:
            logger.debug("[Scheduler] Retrain threshold not yet reached.")


async def _seed_data():
    """Seed training_data.csv into the database if no jobs exist."""
    import pandas as pd
    from sqlalchemy import func, select

    from app.ml.preprocessing import clean_text
    from app.models.job import Job
    from app.services.embedding_service import embedding_service

    seed_path = settings.SEED_DATA_PATH
    if not os.path.exists(seed_path):
        logger.warning(f"[Seed] Seed file not found at {seed_path}. Skipping.")
        return

    async with AsyncSessionLocal() as db:
        count_result = await db.execute(select(func.count(Job.id)))
        if count_result.scalar_one() > 0:
            logger.info("[Seed] DB already has jobs. Skipping seed.")
            return

        logger.info(f"[Seed] Loading seed data from {seed_path}...")
        try:
            df = pd.read_csv(seed_path)
            df = df[["position_title", "job_description"]].dropna().reset_index(drop=True)
        except Exception as e:
            logger.error(f"[Seed] Failed to load CSV: {e}")
            return

        logger.info(f"[Seed] Encoding {len(df)} job descriptions with SBERT...")
        texts = [clean_text(t) for t in df["job_description"].tolist()]
        embeddings = embedding_service.encode_batch(texts, batch_size=64)

        jobs = []
        for i, row in df.iterrows():
            job = Job(
                position_title=row["position_title"],
                description=row["job_description"],
                cleaned_description=texts[i],
                embedding=embeddings[i].tolist(),
                source="seed",
            )
            jobs.append(job)

        db.add_all(jobs)
        await db.commit()
        logger.info(f"[Seed] Seeded {len(jobs)} jobs successfully.")


# ── Startup / Shutdown ────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    logger.info("[Startup] Initializing database...")
    await init_db()

    logger.info("[Startup] Warming up SBERT model...")
    from app.services.embedding_service import embedding_service
    embedding_service.warm_up()

    logger.info("[Startup] Seeding data if needed...")
    await _seed_data()

    logger.info("[Startup] Starting APScheduler...")
    scheduler.add_job(
        _check_and_retrain,
        trigger="interval",
        hours=settings.RETRAIN_SCHEDULE_HOURS,
        id="continual_learning_job",
        replace_existing=True,
    )
    scheduler.start()

    logger.info("[Startup] 🚀 Job Recommendation API v2.0 ready!")


@app.on_event("shutdown")
async def on_shutdown():
    if scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info("[Shutdown] API stopped.")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    from app.services.continual_learning import continual_learner
    return {"status": "ok", "model_version": continual_learner.get_model_version()}
