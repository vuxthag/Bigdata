from app.routers import auth, cvs, jobs, recommend, analytics, users, crawler
from app.routers import candidate_applications, employer_applications
from app.routers import employer_company, employer_jobs

__all__ = [
    "auth", "cvs", "jobs", "recommend", "analytics", "users", "crawler",
    # Phase 2
    "candidate_applications", "employer_applications",
    # Phase 3
    "employer_company", "employer_jobs",
]
