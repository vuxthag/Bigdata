"""
main.py
=======
FastAPI application entry point — Candidate-Only Job Search Platform.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import AsyncSessionLocal, init_db
from app.routers import analytics, auth, cvs, jobs, recommend, users
from app.routers import crawler as crawler_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger(__name__)

# ── Scheduler ─────────────────────────────────────────────────────────────────
scheduler = AsyncIOScheduler()


async def _check_and_retrain():
    """APScheduler job: check threshold and trigger retraining."""
    from app.services.continual_learning import continual_learner

    async with AsyncSessionLocal() as db:
        try:
            if await continual_learner.should_retrain(db):
                logger.info("[Scheduler] Retrain threshold reached. Starting CL cycle...")
                result = await continual_learner.retrain(db)
                logger.info(f"[Scheduler] CL result: {result}")
            else:
                logger.debug("[Scheduler] Retrain threshold not yet reached.")
        except Exception as e:
            logger.error(f"[Scheduler] Error during retrain check: {e}")


async def _seed_data():
    """Seed jobs from CSV into DB if no jobs exist."""
    import pandas as pd
    from sqlalchemy import func, select

    from app.ml.preprocessing import clean_text
    from app.models.job import Job

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
            df = pd.read_csv(seed_path, encoding="utf-8-sig")

            if "jobTitle" in df.columns and "jobDescription" in df.columns:
                df = df.rename(
                    columns={
                        "jobId": "external_job_id",
                        "jobTitle": "position_title",
                        "companyName": "company",
                        "jobUrl": "link",
                        "prettySalary": "pretty_salary",
                        "salaryMin": "salary_min",
                        "salaryMax": "salary_max",
                        "salaryCurrency": "salary_currency",
                        "jobDescription": "job_description",
                        "jobRequirement": "job_requirement",
                        "yearsOfExperience": "years_of_experience",
                        "jobLevel": "job_level",
                        "jobFunction": "job_function",
                        "approvedOn": "approved_on",
                        "expiredOn": "expired_on",
                        "companyId": "company_id",
                        "companyProfile": "company_profile",
                    }
                )
            elif "position_title" in df.columns and "job_description" in df.columns:
                pass
            elif "title" in df.columns and "raw_text" in df.columns:
                df = df[["title", "raw_text", "description", "company", "job_url"]].copy()
                df = df.rename(columns={"title": "position_title", "raw_text": "job_description"})
            else:
                logger.error(f"[Seed] Unrecognised CSV schema. Columns: {list(df.columns)}")
                return

            df = df.dropna(subset=["position_title", "job_description"]).reset_index(drop=True)
        except Exception as e:
            logger.error(f"[Seed] Failed to load CSV: {e}")
            return

        def _norm_int(value):
            if pd.isna(value):
                return None
            s = str(value).strip()
            if not s:
                return None
            try:
                return int(float(s))
            except Exception:
                return None

        def _norm_str(value):
            if pd.isna(value):
                return None
            s = str(value).strip()
            return s or None

        def _norm_datetime(value):
            if pd.isna(value):
                return None
            dt = pd.to_datetime(value, utc=True, errors="coerce")
            if pd.isna(dt):
                return None
            return dt.to_pydatetime()

        def _norm_skills(value):
            if pd.isna(value):
                return None
            skills = [s.strip() for s in str(value).split(",") if s.strip()]
            return skills or None

        logger.info(f"[Seed] Preparing {len(df)} jobs from CSV...")
        job_objects = []
        for row in df.to_dict(orient="records"):
            description = row.get("job_description") or ""
            cleaned_description = clean_text(description)

            job_objects.append(Job(
                position_title=row.get("position_title"),
                description=description,
                cleaned_description=cleaned_description,
                embedding=None,
                source="csv_seed",
                external_job_id=_norm_str(row.get("external_job_id")),
                company=_norm_str(row.get("company")),
                company_id=_norm_str(row.get("company_id")),
                company_profile=_norm_str(row.get("company_profile")),
                location=_norm_str(row.get("location")),
                address=_norm_str(row.get("address")),
                link=_norm_str(row.get("link") or row.get("job_url")),
                skills=_norm_skills(row.get("skills")),
                pretty_salary=_norm_str(row.get("pretty_salary")),
                salary_min=_norm_int(row.get("salary_min")),
                salary_max=_norm_int(row.get("salary_max")),
                salary_currency=_norm_str(row.get("salary_currency")),
                years_of_experience=_norm_int(row.get("years_of_experience")),
                job_level=_norm_str(row.get("job_level")),
                industry=_norm_str(row.get("industry")),
                job_function=_norm_str(row.get("job_function")),
                job_requirement=_norm_str(row.get("job_requirement")),
                benefits=_norm_str(row.get("benefits")),
                approved_on=_norm_datetime(row.get("approved_on")),
                expired_on=_norm_datetime(row.get("expired_on")),
            ))

        db.add_all(job_objects)
        await db.commit()
        logger.info(f"[Seed] Seeded {len(job_objects)} jobs successfully.")


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[Startup] Initializing database...")
    await init_db()

    logger.info("[Startup] Warming up SBERT model...")
    from app.services.embedding_service import embedding_service
    try:
        embedding_service.warm_up()
    except Exception as e:
        logger.error(f"[Startup] SBERT warm-up failed: {e}")

    logger.info("[Startup] Seeding data if needed...")
    try:
        await _seed_data()
    except Exception as e:
        logger.error(f"[Startup] Seed failed: {e}")

    logger.info("[Startup] Starting APScheduler...")
    scheduler.add_job(
        _check_and_retrain,
        trigger="interval",
        hours=settings.RETRAIN_SCHEDULE_HOURS,
        id="continual_learning_job",
        replace_existing=True,
    )

    # VietnamWorks-only crawler
    logger.info("[Startup] Registering VietnamWorks crawler...")
    try:
        from crawler.scheduler import register_crawler_jobs
        register_crawler_jobs(scheduler)
    except Exception as e:
        logger.error(f"[Startup] Failed to register crawler jobs: {e}")

    scheduler.start()

    logger.info("[Startup] Job Search Platform v3.0 ready!")
    yield

    if scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info("[Shutdown] API stopped.")


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Job Search Platform API",
    description="AI-powered job search and CV matching for candidates",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://frontend", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"
ROUTERS = [
    auth.router,
    users.router,
    cvs.router,
    jobs.router,
    recommend.router,
    analytics.router,
    crawler_router.router,
]

for router in ROUTERS:
    app.include_router(router, prefix=PREFIX)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    from app.services.continual_learning import continual_learner
    return {"status": "ok", "model_version": continual_learner.get_model_version()}
