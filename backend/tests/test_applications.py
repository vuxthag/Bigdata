"""
tests/test_applications.py
===========================
End-to-end tests for the Phase 2 application flow.

Test matrix
-----------
Candidate:
  ✓ apply_success              — happy path, 201 + application_id
  ✓ apply_duplicate            — second apply → 409
  ✓ apply_draft_job            — draft job    → 400
  ✓ apply_closed_job           — closed job   → 400
  ✓ apply_nonexistent_job      — unknown job  → 404
  ✓ apply_requires_auth        — no token     → 403/401
  ✓ apply_employer_blocked     — wrong role   → 403
  ✓ list_applications_empty    — new candidate sees empty list
  ✓ list_applications_returns  — after apply, list shows the application

Employer:
  ✓ employer_get_applications  — owns the job, sees applicant
  ✓ employer_foreign_job       — does not own job → 403
  ✓ employer_nonexistent_job   — unknown job      → 404
  ✓ employer_update_status     — applied → reviewed  (valid transition)
  ✓ employer_invalid_transition — applied → hired    (skip steps) → 400
  ✓ employer_update_not_owner  — another employer → 403
  ✓ update_nonexistent_app     — unknown app_id   → 404

Setup strategy
--------------
All tests use pytest-asyncio with an in-memory SQLite engine so the real
Postgres is not required for CI. Heavy ML services (SBERT) are mocked.

Fixtures create minimal User, Job, and Company rows directly through the
service layer / ORM — no HTTP calls for setup to keep tests fast and focused.

Running
-------
    cd backend
    pytest tests/test_applications.py -v
"""
from __future__ import annotations

import uuid
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.base import Base
from app.database import get_db
from app.main import app
from app.models.company import Company
from app.models.job import Job
from app.models.user import User
from app.services.auth_service import create_access_token, hash_password

# ── Test database (SQLite in-memory async) ────────────────────────────────────
# NOTE: SQLite does not enforce CHECK constraints; for full constraint testing
# use pytest-postgresql or a real Postgres instance.
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once per test session."""
    # Import models so SQLAlchemy metadata is populated
    import app.models  # noqa: F401

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional session for each test; roll back after."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(autouse=True)
async def override_db(db_session: AsyncSession):
    """Override FastAPI's get_db dependency with the test session."""
    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    """HTTPX async client backed by the FastAPI test app."""
    # Patch SBERT so importing main.py doesn't try to load the ML model
    with patch(
        "app.services.embedding_service.embedding_service.warm_up",
        return_value=None,
    ), patch(
        "app.services.embedding_service.embedding_service.encode",
        return_value=[0.0] * 384,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


# ── Helper factories ──────────────────────────────────────────────────────────

async def _make_user(
    db: AsyncSession,
    *,
    email: str,
    role: str = "candidate",
    full_name: str | None = "Test User",
) -> tuple[User, str]:
    """Create a user and return (user, jwt_token)."""
    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        full_name=full_name,
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    token, _ = create_access_token(user.id)
    return user, token


async def _make_company(db: AsyncSession, *, owner: User) -> Company:
    """Create a company linked to the given employer."""
    company = Company(
        owner_id=owner.id,
        name=f"ACME Corp {owner.email}",
        slug=f"acme-{owner.id}",
    )
    db.add(company)
    await db.flush()
    return company


async def _make_job(
    db: AsyncSession,
    *,
    company: Company | None = None,
    created_by: uuid.UUID | None = None,
    status: str = "published",
) -> Job:
    """Create a job description."""
    job = Job(
        position_title="Software Engineer",
        description="We need a great engineer.",
        source="test",
        status=status,
        company_id=company.id if company else None,
        created_by=created_by,
        is_active=True,
    )
    db.add(job)
    await db.flush()
    return job


async def _apply(
    client: AsyncClient,
    token: str,
    job_id: uuid.UUID,
    cv_id: uuid.UUID | None = None,
    cover_letter: str | None = None,
):
    """POST /api/v1/candidate/applications — convenience wrapper."""
    body: dict = {"job_id": str(job_id)}
    if cv_id:
        body["cv_id"] = str(cv_id)
    if cover_letter:
        body["cover_letter"] = cover_letter
    return await client.post(
        "/api/v1/candidate/applications",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )


# ═════════════════════════════════════════════════════════════════════════════
# Candidate tests
# ═════════════════════════════════════════════════════════════════════════════

class TestCandidateApply:
    """POST /api/v1/candidate/applications"""

    @pytest.mark.asyncio
    async def test_apply_success(self, client: AsyncClient, db_session: AsyncSession):
        """A candidate can apply to a published job and receives application_id."""
        candidate, token = await _make_user(db_session, email="c1@test.com", role="candidate")
        employer, _ = await _make_user(db_session, email="e1@test.com", role="employer")
        company = await _make_company(db_session, owner=employer)
        job = await _make_job(db_session, company=company, status="published")
        await db_session.commit()

        resp = await _apply(client, token, job.id, cover_letter="Hello!")
        assert resp.status_code == 201, resp.json()
        data = resp.json()
        assert data["message"] == "Application submitted successfully"
        assert "application_id" in data
        # Must be a valid UUID
        uuid.UUID(data["application_id"])

    @pytest.mark.asyncio
    async def test_apply_updates_applicant_count(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """applicant_count on job_descriptions increments after a successful apply."""
        from sqlalchemy import select

        candidate, token = await _make_user(db_session, email="c2@test.com", role="candidate")
        employer, _ = await _make_user(db_session, email="e2@test.com", role="employer")
        company = await _make_company(db_session, owner=employer)
        job = await _make_job(db_session, company=company, status="published")
        await db_session.commit()

        resp = await _apply(client, token, job.id)
        assert resp.status_code == 201

        # Read applicant count directly from DB
        result = await db_session.execute(select(Job.applicant_count).where(Job.id == job.id))
        count = result.scalar_one()
        assert count == 1

    @pytest.mark.asyncio
    async def test_apply_duplicate_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Applying to the same job twice returns 409 Conflict."""
        candidate, token = await _make_user(db_session, email="c3@test.com", role="candidate")
        employer, _ = await _make_user(db_session, email="e3@test.com", role="employer")
        company = await _make_company(db_session, owner=employer)
        job = await _make_job(db_session, company=company, status="published")
        await db_session.commit()

        resp1 = await _apply(client, token, job.id)
        assert resp1.status_code == 201

        resp2 = await _apply(client, token, job.id)
        assert resp2.status_code == 409
        assert "already applied" in resp2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_apply_draft_job_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Applying to a draft job returns 400 Bad Request."""
        candidate, token = await _make_user(db_session, email="c4@test.com", role="candidate")
        job = await _make_job(db_session, status="draft")
        await db_session.commit()

        resp = await _apply(client, token, job.id)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_apply_closed_job_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Applying to a closed job returns 400 Bad Request."""
        candidate, token = await _make_user(db_session, email="c5@test.com", role="candidate")
        job = await _make_job(db_session, status="closed")
        await db_session.commit()

        resp = await _apply(client, token, job.id)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_apply_nonexistent_job_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Applying to a non-existent job UUID returns 404."""
        _, token = await _make_user(db_session, email="c6@test.com", role="candidate")
        await db_session.commit()

        resp = await _apply(client, token, uuid.uuid4())
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_apply_requires_auth(self, client: AsyncClient, db_session: AsyncSession):
        """Calling without a token returns 403 (HTTPBearer) or 401."""
        job = await _make_job(db_session, status="published")
        await db_session.commit()

        resp = await client.post(
            "/api/v1/candidate/applications",
            json={"job_id": str(job.id)},
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_apply_employer_role_blocked(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """An employer token must NOT be able to apply to a job."""
        employer, token = await _make_user(db_session, email="e4@test.com", role="employer")
        job = await _make_job(db_session, status="published")
        await db_session.commit()

        resp = await _apply(client, token, job.id)
        assert resp.status_code == 403


class TestCandidateListApplications:
    """GET /api/v1/candidate/applications"""

    @pytest.mark.asyncio
    async def test_list_empty_for_new_candidate(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """A brand-new candidate with no applications gets an empty list."""
        _, token = await _make_user(db_session, email="cl1@test.com", role="candidate")
        await db_session.commit()

        resp = await client.get(
            "/api/v1/candidate/applications",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_shows_applied_jobs(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """After applying, the list endpoint returns that application."""
        candidate, token = await _make_user(db_session, email="cl2@test.com", role="candidate")
        employer, _ = await _make_user(db_session, email="el2@test.com", role="employer")
        company = await _make_company(db_session, owner=employer)
        job = await _make_job(db_session, company=company, status="published")
        await db_session.commit()

        apply_resp = await _apply(client, token, job.id, cover_letter="I'm interested")
        assert apply_resp.status_code == 201

        list_resp = await client.get(
            "/api/v1/candidate/applications",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["status"] == "applied"
        assert item["job"]["title"] == "Software Engineer"
        assert item["job"]["company_name"] == company.name
        assert item["cover_letter"] == "I'm interested"

    @pytest.mark.asyncio
    async def test_list_isolated_per_candidate(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Each candidate sees only their own applications."""
        c1, t1 = await _make_user(db_session, email="cl3a@test.com", role="candidate")
        c2, t2 = await _make_user(db_session, email="cl3b@test.com", role="candidate")
        employer, _ = await _make_user(db_session, email="el3@test.com", role="employer")
        company = await _make_company(db_session, owner=employer)
        job = await _make_job(db_session, company=company, status="published")
        await db_session.commit()

        await _apply(client, t1, job.id)

        resp_c2 = await client.get(
            "/api/v1/candidate/applications",
            headers={"Authorization": f"Bearer {t2}"},
        )
        data = resp_c2.json()
        assert data["total"] == 0  # c2 never applied


# ═════════════════════════════════════════════════════════════════════════════
# Employer tests
# ═════════════════════════════════════════════════════════════════════════════

class TestEmployerGetApplications:
    """GET /api/v1/employer/applications/{job_id}"""

    @pytest.mark.asyncio
    async def test_employer_sees_own_job_applicants(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Employer who owns the job can see the applicant list."""
        employer, emp_token = await _make_user(db_session, email="emp1@test.com", role="employer")
        company = await _make_company(db_session, owner=employer)
        job = await _make_job(db_session, company=company, status="published")
        candidate, cand_token = await _make_user(db_session, email="cand1@test.com", role="candidate")
        await db_session.commit()

        await _apply(client, cand_token, job.id, cover_letter="Hire me!")

        resp = await client.get(
            f"/api/v1/employer/applications/{job.id}",
            headers={"Authorization": f"Bearer {emp_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["job_id"] == str(job.id)
        item = data["items"][0]
        assert item["candidate"]["email"] == "cand1@test.com"
        assert item["status"] == "applied"
        assert item["cover_letter"] == "Hire me!"
        assert item["match_score"] is None

    @pytest.mark.asyncio
    async def test_employer_blocked_for_other_employer_job(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Employer cannot view applications for a job they don't own."""
        owner, _ = await _make_user(db_session, email="emp2a@test.com", role="employer")
        intruder, intruder_token = await _make_user(db_session, email="emp2b@test.com", role="employer")
        company = await _make_company(db_session, owner=owner)
        job = await _make_job(db_session, company=company, status="published")
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/employer/applications/{job.id}",
            headers={"Authorization": f"Bearer {intruder_token}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_employer_nonexistent_job_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Requesting applications for a non-existent job returns 404."""
        employer, token = await _make_user(db_session, email="emp3@test.com", role="employer")
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/employer/applications/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_candidate_blocked_from_employer_endpoint(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """A candidate token returns 403 on the employer endpoint."""
        candidate, cand_token = await _make_user(db_session, email="emp4c@test.com", role="candidate")
        employer, _ = await _make_user(db_session, email="emp4e@test.com", role="employer")
        company = await _make_company(db_session, owner=employer)
        job = await _make_job(db_session, company=company, status="published")
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/employer/applications/{job.id}",
            headers={"Authorization": f"Bearer {cand_token}"},
        )
        assert resp.status_code == 403


class TestEmployerUpdateStatus:
    """PATCH /api/v1/employer/applications/{application_id}/status"""

    async def _setup(self, db_session, client):
        """Return (employer_token, application_id) after creating a full application."""
        employer, emp_token = await _make_user(db_session, email=f"eu_{uuid.uuid4().hex[:6]}@test.com", role="employer")
        company = await _make_company(db_session, owner=employer)
        job = await _make_job(db_session, company=company, status="published")
        candidate, cand_token = await _make_user(db_session, email=f"cu_{uuid.uuid4().hex[:6]}@test.com", role="candidate")
        await db_session.commit()

        apply_resp = await _apply(client, cand_token, job.id)
        assert apply_resp.status_code == 201
        app_id = apply_resp.json()["application_id"]
        return emp_token, app_id

    @pytest.mark.asyncio
    async def test_update_status_valid_transition(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """applied → reviewed is a valid transition and returns 200."""
        emp_token, app_id = await self._setup(db_session, client)

        resp = await client.patch(
            f"/api/v1/employer/applications/{app_id}/status",
            json={"status": "reviewed"},
            headers={"Authorization": f"Bearer {emp_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Status updated successfully"
        assert data["new_status"] == "reviewed"
        assert data["application_id"] == app_id

    @pytest.mark.asyncio
    async def test_update_status_invalid_transition(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """applied → hired skips required steps and must return 400."""
        emp_token, app_id = await self._setup(db_session, client)

        resp = await client.patch(
            f"/api/v1/employer/applications/{app_id}/status",
            json={"status": "hired"},
            headers={"Authorization": f"Bearer {emp_token}"},
        )
        assert resp.status_code == 400
        assert "invalid" in resp.json()["detail"].lower() or "transition" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_status_full_pipeline(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Walk the full happy-path pipeline: applied→reviewed→interview→offered→hired."""
        emp_token, app_id = await self._setup(db_session, client)
        pipeline = ["reviewed", "interview", "offered", "hired"]

        for next_status in pipeline:
            resp = await client.patch(
                f"/api/v1/employer/applications/{app_id}/status",
                json={"status": next_status},
                headers={"Authorization": f"Bearer {emp_token}"},
            )
            assert resp.status_code == 200, f"Failed on transition to {next_status}: {resp.json()}"
            assert resp.json()["new_status"] == next_status

    @pytest.mark.asyncio
    async def test_update_status_other_employer_blocked(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Another employer cannot update a status for a job they don't own."""
        _, app_id = await self._setup(db_session, client)
        # Create a second, unrelated employer
        intruder, intruder_token = await _make_user(
            db_session, email=f"intruder_{uuid.uuid4().hex[:6]}@test.com", role="employer"
        )
        await db_session.commit()

        resp = await client.patch(
            f"/api/v1/employer/applications/{app_id}/status",
            json={"status": "reviewed"},
            headers={"Authorization": f"Bearer {intruder_token}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_update_nonexistent_application_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """PATCH on a non-existent application UUID returns 404."""
        employer, token = await _make_user(db_session, email=f"eu404_{uuid.uuid4().hex[:6]}@test.com", role="employer")
        await db_session.commit()

        resp = await client.patch(
            f"/api/v1/employer/applications/{uuid.uuid4()}/status",
            json={"status": "reviewed"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_reject_at_any_stage(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """An employer can reject an application from any non-terminal state."""
        emp_token, app_id = await self._setup(db_session, client)

        # Move to interview first
        await client.patch(
            f"/api/v1/employer/applications/{app_id}/status",
            json={"status": "reviewed"},
            headers={"Authorization": f"Bearer {emp_token}"},
        )
        await client.patch(
            f"/api/v1/employer/applications/{app_id}/status",
            json={"status": "interview"},
            headers={"Authorization": f"Bearer {emp_token}"},
        )

        # Now reject from interview
        resp = await client.patch(
            f"/api/v1/employer/applications/{app_id}/status",
            json={"status": "rejected"},
            headers={"Authorization": f"Bearer {emp_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["new_status"] == "rejected"

    @pytest.mark.asyncio
    async def test_terminal_state_cannot_be_changed(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Once rejected, the status cannot be changed further."""
        emp_token, app_id = await self._setup(db_session, client)

        # Reject immediately
        await client.patch(
            f"/api/v1/employer/applications/{app_id}/status",
            json={"status": "rejected"},
            headers={"Authorization": f"Bearer {emp_token}"},
        )

        # Try to re-open — must fail
        resp = await client.patch(
            f"/api/v1/employer/applications/{app_id}/status",
            json={"status": "reviewed"},
            headers={"Authorization": f"Bearer {emp_token}"},
        )
        assert resp.status_code == 400
