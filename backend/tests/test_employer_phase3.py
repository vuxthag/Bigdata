"""
tests/test_employer_phase3.py
==============================
End-to-end tests for Phase 3 — Employer Core System.

Test matrix
-----------
Company:
  ✓ create_company_success
  ✓ create_company_duplicate         → 409
  ✓ create_company_candidate_blocked → 403
  ✓ get_company_me
  ✓ get_company_not_created          → 404
  ✓ update_company_fields
  ✓ update_company_not_created       → 404

Job lifecycle:
  ✓ create_job_draft
  ✓ create_job_no_company            → 400
  ✓ create_job_candidate_blocked     → 403
  ✓ list_jobs_empty
  ✓ list_jobs_with_status_filter
  ✓ get_job_detail
  ✓ get_job_other_employer           → 403
  ✓ update_job_draft
  ✓ update_job_closed                → 400
  ✓ publish_job
  ✓ publish_already_published        → 400
  ✓ close_job
  ✓ close_already_closed             → 400
  ✓ delete_draft_job
  ✓ delete_published_job             → 400
  ✓ delete_closed_job                → 400

Security:
  ✓ access_other_employer_job        → 403
  ✓ update_other_employer_job        → 403
  ✓ publish_other_employer_job       → 403

All tests use in-memory SQLite via the same session override as test_applications.py.
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
from app.models.user import User
from app.services.auth_service import create_access_token, hash_password

# ── Test database ─────────────────────────────────────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Session-scoped table creation ─────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    import app.models  # noqa: F401 — registers all ORM metadata
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(autouse=True)
async def override_db(db_session: AsyncSession):
    async def _get_test_db():
        yield db_session
    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    with patch("app.services.embedding_service.embedding_service.warm_up", return_value=None), \
         patch("app.services.embedding_service.embedding_service.encode", return_value=[0.0] * 384):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


# ── Helpers ───────────────────────────────────────────────────────────────────

def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _make_user(
    db: AsyncSession,
    *,
    email: str,
    role: str = "employer",
) -> tuple[User, str]:
    user = User(
        email=email,
        hashed_password=hash_password("pass1234"),
        full_name="Test User",
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    token, _ = create_access_token(user.id)
    return user, token


async def _create_company_via_api(
    client: AsyncClient,
    token: str,
    name: str = "ACME Inc",
) -> dict:
    resp = await client.post(
        "/api/v1/employer/company",
        json={"name": name},
        headers=_auth(token),
    )
    return resp


async def _create_job_via_api(
    client: AsyncClient,
    token: str,
    title: str = "Backend Engineer",
    description: str = "We need a great backend engineer for our team.",
) -> dict:
    return await client.post(
        "/api/v1/employer/jobs",
        json={"position_title": title, "description": description},
        headers=_auth(token),
    )


# ═════════════════════════════════════════════════════════════════════════════
# Company tests
# ═════════════════════════════════════════════════════════════════════════════

class TestCompanyCRUD:

    @pytest.mark.asyncio
    async def test_create_company_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Employer can create a company and receives id, name, slug."""
        employer, token = await _make_user(db_session, email="comp1@test.com")
        await db_session.commit()

        resp = await _create_company_via_api(client, token, "Tech Ventures")
        assert resp.status_code == 201, resp.json()
        data = resp.json()
        assert data["name"] == "Tech Ventures"
        assert data["slug"] == "tech-ventures"
        assert "id" in data
        uuid.UUID(data["id"])

    @pytest.mark.asyncio
    async def test_create_company_slug_auto_generated(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Slug is lower-cased and special chars are stripped."""
        employer, token = await _make_user(db_session, email="comp2@test.com")
        await db_session.commit()

        resp = await _create_company_via_api(client, token, "Acme Corp & Partners!")
        assert resp.status_code == 201
        assert resp.json()["slug"] == "acme-corp-partners"

    @pytest.mark.asyncio
    async def test_create_company_duplicate_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """A second company creation attempt returns 409."""
        _, token = await _make_user(db_session, email="comp3@test.com")
        await db_session.commit()

        await _create_company_via_api(client, token, "First Corp")
        resp2 = await _create_company_via_api(client, token, "Second Corp")
        assert resp2.status_code == 409

    @pytest.mark.asyncio
    async def test_create_company_candidate_returns_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """A candidate token cannot create a company."""
        _, token = await _make_user(db_session, email="cand1@test.com", role="candidate")
        await db_session.commit()

        resp = await _create_company_via_api(client, token)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_get_company_me(self, client: AsyncClient, db_session: AsyncSession):
        """GET /employer/company/me returns full profile after creation."""
        _, token = await _make_user(db_session, email="comp4@test.com")
        await db_session.commit()

        await _create_company_via_api(client, token, "My Corp")
        resp = await client.get("/api/v1/employer/company/me", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "My Corp"
        assert data["slug"] == "my-corp"
        assert "owner_id" in data

    @pytest.mark.asyncio
    async def test_get_company_me_before_creation_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Employer without a company gets 404 on GET /employer/company/me."""
        _, token = await _make_user(db_session, email="comp5@test.com")
        await db_session.commit()

        resp = await client.get("/api/v1/employer/company/me", headers=_auth(token))
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_company_fields(self, client: AsyncClient, db_session: AsyncSession):
        """PUT /employer/company/me updates specified fields."""
        _, token = await _make_user(db_session, email="comp6@test.com")
        await db_session.commit()

        await _create_company_via_api(client, token, "Old Name")
        resp = await client.put(
            "/api/v1/employer/company/me",
            json={
                "name": "New Name",
                "industry": "Technology",
                "size": "11-50",
                "location": "Ha Noi",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Name"
        assert data["slug"] == "new-name"
        assert data["industry"] == "Technology"
        assert data["size"] == "11-50"
        assert data["location"] == "Ha Noi"

    @pytest.mark.asyncio
    async def test_update_company_before_creation_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """PUT without prior company creation returns 404."""
        _, token = await _make_user(db_session, email="comp7@test.com")
        await db_session.commit()

        resp = await client.put(
            "/api/v1/employer/company/me",
            json={"name": "Ghost Corp"},
            headers=_auth(token),
        )
        assert resp.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# Job lifecycle tests
# ═════════════════════════════════════════════════════════════════════════════

class TestJobLifecycle:

    async def _setup_employer_with_company(
        self, db_session: AsyncSession, client: AsyncClient, email: str
    ) -> tuple[str, str]:
        """Create employer + company, return (token, company_name)."""
        _, token = await _make_user(db_session, email=email)
        await db_session.commit()
        co_resp = await _create_company_via_api(client, token, f"Corp {email}")
        assert co_resp.status_code == 201
        return token, co_resp.json()["name"]

    @pytest.mark.asyncio
    async def test_create_job_draft(self, client: AsyncClient, db_session: AsyncSession):
        """An employer with a company can create a draft job."""
        token, _ = await self._setup_employer_with_company(
            db_session, client, "job1@test.com"
        )
        resp = await _create_job_via_api(client, token)
        assert resp.status_code == 201, resp.json()
        data = resp.json()
        assert data["status"] == "draft"
        assert "job_id" in data
        uuid.UUID(data["job_id"])

    @pytest.mark.asyncio
    async def test_create_job_without_company_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Employer without a company gets 400 when creating a job."""
        _, token = await _make_user(db_session, email="job2@test.com")
        await db_session.commit()

        resp = await _create_job_via_api(client, token)
        assert resp.status_code == 400
        assert "company" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_job_candidate_returns_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Candidate token cannot create a job."""
        _, token = await _make_user(db_session, email="job3@test.com", role="candidate")
        await db_session.commit()

        resp = await _create_job_via_api(client, token)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_list_jobs_empty(self, client: AsyncClient, db_session: AsyncSession):
        """Fresh employer sees empty job list."""
        token, _ = await self._setup_employer_with_company(
            db_session, client, "job4@test.com"
        )
        resp = await client.get("/api/v1/employer/jobs", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_jobs_with_status_filter(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Status filter returns only matching jobs."""
        token, _ = await self._setup_employer_with_company(
            db_session, client, "job5@test.com"
        )
        # Create 2 drafts
        await _create_job_via_api(client, token, "Job A", "Description for job A position.")
        create_resp = await _create_job_via_api(client, token, "Job B", "Description for job B position.")
        job_b_id = create_resp.json()["job_id"]

        # Publish Job B
        await client.patch(
            f"/api/v1/employer/jobs/{job_b_id}/publish",
            headers=_auth(token),
        )

        draft_resp = await client.get(
            "/api/v1/employer/jobs?status=draft", headers=_auth(token)
        )
        assert draft_resp.json()["total"] == 1
        assert draft_resp.json()["items"][0]["position_title"] == "Job A"

        pub_resp = await client.get(
            "/api/v1/employer/jobs?status=published", headers=_auth(token)
        )
        assert pub_resp.json()["total"] == 1
        assert pub_resp.json()["items"][0]["position_title"] == "Job B"

    @pytest.mark.asyncio
    async def test_get_job_detail(self, client: AsyncClient, db_session: AsyncSession):
        """Employer can retrieve full job detail by ID."""
        token, _ = await self._setup_employer_with_company(
            db_session, client, "job6@test.com"
        )
        create_resp = await _create_job_via_api(client, token, "Senior Dev", "Looking for a senior developer with 5+ years of experience.")
        job_id = create_resp.json()["job_id"]

        resp = await client.get(f"/api/v1/employer/jobs/{job_id}", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["position_title"] == "Senior Dev"
        assert data["status"] == "draft"
        assert data["company"] is not None

    @pytest.mark.asyncio
    async def test_get_job_other_employer_returns_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Employer B cannot see Employer A's job."""
        token_a, _ = await self._setup_employer_with_company(
            db_session, client, "job7a@test.com"
        )
        token_b, _ = await self._setup_employer_with_company(
            db_session, client, "job7b@test.com"
        )
        create_resp = await _create_job_via_api(client, token_a)
        job_id = create_resp.json()["job_id"]

        resp = await client.get(f"/api/v1/employer/jobs/{job_id}", headers=_auth(token_b))
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_update_job_draft(self, client: AsyncClient, db_session: AsyncSession):
        """Employer can update a draft job's fields."""
        token, _ = await self._setup_employer_with_company(
            db_session, client, "job8@test.com"
        )
        create_resp = await _create_job_via_api(client, token)
        job_id = create_resp.json()["job_id"]

        resp = await client.put(
            f"/api/v1/employer/jobs/{job_id}",
            json={
                "position_title": "Updated Title",
                "location": "Ho Chi Minh City",
                "salary_min": 1500,
                "salary_max": 3000,
                "job_type": "remote",
            },
            headers=_auth(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["position_title"] == "Updated Title"
        assert data["location"] == "Ho Chi Minh City"
        assert data["salary_min"] == 1500
        assert data["job_type"] == "remote"

    @pytest.mark.asyncio
    async def test_update_closed_job_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Closed jobs cannot be edited."""
        token, _ = await self._setup_employer_with_company(
            db_session, client, "job9@test.com"
        )
        create_resp = await _create_job_via_api(client, token)
        job_id = create_resp.json()["job_id"]

        # Close it
        await client.patch(f"/api/v1/employer/jobs/{job_id}/close", headers=_auth(token))

        resp = await client.put(
            f"/api/v1/employer/jobs/{job_id}",
            json={"position_title": "Try to Edit"},
            headers=_auth(token),
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_publish_job(self, client: AsyncClient, db_session: AsyncSession):
        """Employer can publish a draft job; response shows status=published."""
        token, _ = await self._setup_employer_with_company(
            db_session, client, "job10@test.com"
        )
        create_resp = await _create_job_via_api(client, token)
        job_id = create_resp.json()["job_id"]

        resp = await client.patch(
            f"/api/v1/employer/jobs/{job_id}/publish", headers=_auth(token)
        )
        assert resp.status_code == 200, resp.json()
        data = resp.json()
        assert data["status"] == "published"
        assert data["job_id"] == job_id

    @pytest.mark.asyncio
    async def test_publish_already_published_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Publishing an already-published job returns 400."""
        token, _ = await self._setup_employer_with_company(
            db_session, client, "job11@test.com"
        )
        create_resp = await _create_job_via_api(client, token)
        job_id = create_resp.json()["job_id"]

        await client.patch(f"/api/v1/employer/jobs/{job_id}/publish", headers=_auth(token))
        resp = await client.patch(
            f"/api/v1/employer/jobs/{job_id}/publish", headers=_auth(token)
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_close_published_job(self, client: AsyncClient, db_session: AsyncSession):
        """Employer can close a published job."""
        token, _ = await self._setup_employer_with_company(
            db_session, client, "job12@test.com"
        )
        create_resp = await _create_job_via_api(client, token)
        job_id = create_resp.json()["job_id"]

        await client.patch(f"/api/v1/employer/jobs/{job_id}/publish", headers=_auth(token))
        resp = await client.patch(
            f"/api/v1/employer/jobs/{job_id}/close", headers=_auth(token)
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"

    @pytest.mark.asyncio
    async def test_close_already_closed_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Closing an already-closed job returns 400."""
        token, _ = await self._setup_employer_with_company(
            db_session, client, "job13@test.com"
        )
        create_resp = await _create_job_via_api(client, token)
        job_id = create_resp.json()["job_id"]

        await client.patch(f"/api/v1/employer/jobs/{job_id}/close", headers=_auth(token))
        resp = await client.patch(
            f"/api/v1/employer/jobs/{job_id}/close", headers=_auth(token)
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_draft_job(self, client: AsyncClient, db_session: AsyncSession):
        """Employer can hard-delete a draft job."""
        token, _ = await self._setup_employer_with_company(
            db_session, client, "job14@test.com"
        )
        create_resp = await _create_job_via_api(client, token)
        job_id = create_resp.json()["job_id"]

        resp = await client.delete(
            f"/api/v1/employer/jobs/{job_id}", headers=_auth(token)
        )
        assert resp.status_code == 200

        # Verify it is gone
        get_resp = await client.get(
            f"/api/v1/employer/jobs/{job_id}", headers=_auth(token)
        )
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_published_job_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Published jobs cannot be deleted."""
        token, _ = await self._setup_employer_with_company(
            db_session, client, "job15@test.com"
        )
        create_resp = await _create_job_via_api(client, token)
        job_id = create_resp.json()["job_id"]

        await client.patch(f"/api/v1/employer/jobs/{job_id}/publish", headers=_auth(token))
        resp = await client.delete(
            f"/api/v1/employer/jobs/{job_id}", headers=_auth(token)
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_closed_job_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Closed jobs cannot be deleted."""
        token, _ = await self._setup_employer_with_company(
            db_session, client, "job16@test.com"
        )
        create_resp = await _create_job_via_api(client, token)
        job_id = create_resp.json()["job_id"]

        await client.patch(f"/api/v1/employer/jobs/{job_id}/close", headers=_auth(token))
        resp = await client.delete(
            f"/api/v1/employer/jobs/{job_id}", headers=_auth(token)
        )
        assert resp.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# Security / cross-employer isolation tests
# ═════════════════════════════════════════════════════════════════════════════

class TestEmployerSecurity:

    async def _make_employer_with_job(
        self, db_session: AsyncSession, client: AsyncClient, email: str
    ) -> tuple[str, str]:
        """Return (token, job_id) for a fresh employer with company + draft job."""
        _, token = await _make_user(db_session, email=email)
        await db_session.commit()
        await _create_company_via_api(client, token, f"Corp {email}")
        create_resp = await _create_job_via_api(client, token)
        assert create_resp.status_code == 201
        return token, create_resp.json()["job_id"]

    @pytest.mark.asyncio
    async def test_cannot_get_other_employer_job(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, job_id = await self._make_employer_with_job(
            db_session, client, "sec1a@test.com"
        )
        _, token_b = await _make_user(db_session, email="sec1b@test.com")
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/employer/jobs/{job_id}", headers=_auth(token_b)
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_cannot_update_other_employer_job(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, job_id = await self._make_employer_with_job(
            db_session, client, "sec2a@test.com"
        )
        _, token_b = await _make_user(db_session, email="sec2b@test.com")
        await db_session.commit()

        resp = await client.put(
            f"/api/v1/employer/jobs/{job_id}",
            json={"position_title": "Hacked"},
            headers=_auth(token_b),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_cannot_publish_other_employer_job(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, job_id = await self._make_employer_with_job(
            db_session, client, "sec3a@test.com"
        )
        _, token_b = await _make_user(db_session, email="sec3b@test.com")
        await db_session.commit()

        resp = await client.patch(
            f"/api/v1/employer/jobs/{job_id}/publish",
            headers=_auth(token_b),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_cannot_delete_other_employer_job(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, job_id = await self._make_employer_with_job(
            db_session, client, "sec4a@test.com"
        )
        _, token_b = await _make_user(db_session, email="sec4b@test.com")
        await db_session.commit()

        resp = await client.delete(
            f"/api/v1/employer/jobs/{job_id}",
            headers=_auth(token_b),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_job_appears_in_public_listing_when_published(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Jobs published by employer become visible in public GET /jobs."""
        _, token = await _make_user(db_session, email="sec5@test.com")
        await db_session.commit()
        await _create_company_via_api(client, token, "Public Corp")
        create_resp = await _create_job_via_api(
            client, token, "Public Engineer",
            "This position requires extensive public-facing skills and experience."
        )
        job_id = create_resp.json()["job_id"]
        await client.patch(
            f"/api/v1/employer/jobs/{job_id}/publish", headers=_auth(token)
        )

        # Check public listing (no auth required)
        public_resp = await client.get("/api/v1/jobs?search=Public+Engineer")
        assert public_resp.status_code == 200
        titles = [j["position_title"] for j in public_resp.json()["items"]]
        assert "Public Engineer" in titles
