"""Test configuration: environment override, in-memory DB, fake clients,
JWT-based auth fixtures.

Loaded by pytest before any test module imports — that's intentional. We:

1. Force test-only env vars *before* anything imports ``app.*`` so the
   pydantic-settings ``Settings`` instance freezes to test values rather than
   loading the project's real .env.
2. Build a separate in-memory SQLite engine for tests, with the schema
   recreated per-test so each test sees an empty database.
3. Override ``get_db`` so routes hit the test database, and provide fixtures
   that override ``get_wazuh`` / ``get_ansible`` with scriptable fakes.
4. Provide ``make_user``, ``token_for``, ``auth_header`` and
   ``approver_header`` fixtures so tests can drive the JWT-based auth surface
   without each test building users by hand.
"""

# ---------- 1. Test environment (must run before app imports) ---------------
import os

_TEST_ENV = {
    "DATABASE_URL":     "sqlite:///:memory:",
    "WAZUH_API_URL":    "http://wazuh.test",
    "WAZUH_API_USER":   "test",
    "WAZUH_API_PASSWORD": "test",
    "WAZUH_VERIFY_TLS": "false",
    "WAZUH_INDEXER_URL": "http://indexer.test",
    "WAZUH_INDEXER_USER": "test",
    "WAZUH_INDEXER_PASSWORD": "test",
    "WAZUH_INDEXER_VERIFY_TLS": "false",
    "AWX_API_URL":      "http://awx.test",
    "AWX_API_TOKEN":    "test-token",
    "AWX_VERIFY_TLS":   "false",
    # Mirrors the legacy hardcoded mapping so existing test assertions
    # (template_id == 10 for package_update, etc.) keep working.
    "AWX_TEMPLATE_PACKAGE_UPDATE":  "10",
    "AWX_TEMPLATE_WINDOWS_UPDATE":  "20",
    "AWX_TEMPLATE_SERVICE_RESTART": "30",
    "AWX_TEMPLATE_CONFIG_CHANGE":   "40",
    # 64+ chars so PyJWT does not warn about HMAC key length under HS256.
    "JWT_SECRET":       "test-jwt-secret-test-jwt-secret-test-jwt-secret-test-jwt-secret",
    "CORS_ALLOW_ORIGINS": "",
}
for _k, _v in _TEST_ENV.items():
    os.environ[_k] = _v

# ---------- 2. Stdlib / 3rd-party imports -----------------------------------
from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ---------- 3. App imports (now use the test env above) ---------------------
from app.api.dependencies import get_ansible, get_wazuh
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
# ``app.main`` transitively imports the routes, which import the models, so
# Base.metadata is fully populated by the time we hit it below. Doing
# ``import app.models`` here as well would rebind the local name ``app`` to
# the package and shadow the FastAPI instance imported on the next line.
from app.main import app
from app.models import Role, User
from app.services.ansible_client import AnsibleError
from app.services.wazuh_client import WazuhError


# ---------- Engine + session factory ---------------------------------------

# StaticPool keeps the same connection across the engine, which is required
# for in-memory SQLite to see the same database across requests in a single
# test process.
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def _enable_sqlite_fk(dbapi_conn: Any, _record: Any) -> None:
    """SQLite ignores FK constraints by default. Enable them so tests catch
    real referential bugs (matches PostgreSQL behavior in production)."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


# ---------- Schema reset (per test) ----------------------------------------

@pytest.fixture(autouse=True)
def _reset_schema() -> None:
    """Drop + create all tables before each test for full isolation."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)


# ---------- Dependency overrides --------------------------------------------

def _override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


# Install once; never need to remove.
app.dependency_overrides[get_db] = _override_get_db


# ---------- Fakes for external API clients ---------------------------------

class FakeWazuh:
    """Scriptable Wazuh client double.

    Usage in a test::

        fake_wazuh.agents = [{...}]
        fake_wazuh.vulns_by_agent = {'001': [{...}]}
    """

    def __init__(self) -> None:
        self.agents: list[dict] = []
        self.vulns_by_agent: dict[str, list[dict]] = {}
        self.health_ok: bool = True

    async def health(self) -> dict:
        if not self.health_ok:
            raise WazuhError("simulated wazuh down")
        return {"data": {"info": {"version": "test"}}}

    async def list_agents(self, *, limit: int = 500) -> list[dict]:
        if not self.health_ok:
            raise WazuhError("simulated wazuh down")
        return list(self.agents)

    async def list_vulnerabilities(
        self, agent_id: str, *, limit: int = 500,
    ) -> list[dict]:
        if not self.health_ok:
            raise WazuhError("simulated wazuh down")
        return list(self.vulns_by_agent.get(agent_id, []))

    async def aclose(self) -> None:
        pass


class FakeAwx:
    """Scriptable AWX client double."""

    def __init__(self) -> None:
        self.health_ok: bool = True
        self.next_job_id: int = 1000
        self.job_status: str = "successful"
        self.launches: list[tuple[int, dict]] = []

    async def health(self) -> dict:
        if not self.health_ok:
            raise AnsibleError("simulated awx down")
        return {"version": "test"}

    async def launch_job_template(
        self, template_id: int, *, extra_vars: dict | None = None,
    ) -> dict:
        if not self.health_ok:
            raise AnsibleError("simulated awx down")
        jid = self.next_job_id
        self.next_job_id += 1
        self.launches.append((template_id, dict(extra_vars or {})))
        return {"id": jid, "status": "pending", "extra_vars": extra_vars}

    async def get_job(self, job_id: int) -> dict:
        if not self.health_ok:
            raise AnsibleError("simulated awx down")
        return {"id": job_id, "status": self.job_status}

    async def aclose(self) -> None:
        pass


@pytest.fixture
def fake_wazuh() -> AsyncIterator[FakeWazuh]:
    """Per-test FakeWazuh that replaces ``get_wazuh`` for the test's duration."""
    fake = FakeWazuh()

    async def _yield():
        yield fake

    app.dependency_overrides[get_wazuh] = _yield
    yield fake
    app.dependency_overrides.pop(get_wazuh, None)


@pytest.fixture
def fake_awx() -> AsyncIterator[FakeAwx]:
    fake = FakeAwx()

    async def _yield():
        yield fake

    app.dependency_overrides[get_ansible] = _yield
    yield fake
    app.dependency_overrides.pop(get_ansible, None)


# ---------- TestClient + DB fixtures ---------------------------------------

@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db():
    """Direct DB session for arrange-time setup in tests.

    Uses the same engine the app sees (via the get_db override), so anything
    inserted here is visible to subsequent route calls.
    """
    s = TestSession()
    try:
        yield s
    finally:
        s.close()


# ---------- Auth fixtures (JWT-based) --------------------------------------

@pytest.fixture
def make_user(db) -> Callable[..., User]:
    """Factory: create a user with the given role names and flags.

    Roles are auto-created if they don't exist yet. Returns the User.
    Default is a superuser admin so existing tests keep working without
    each one having to wire up scope rows.
    """

    def _make(
        username: str,
        *,
        role_names: tuple[str, ...] = ("admin",),
        is_superuser: bool = True,
        is_active: bool = True,
        password: str = "testpass",
    ) -> User:
        # Ensure every role exists.
        existing = {
            r.name: r
            for r in db.execute(
                select(Role).where(Role.name.in_(role_names))
            ).scalars().all()
        }
        for name in role_names:
            if name not in existing:
                role = Role(name=name)
                db.add(role)
                db.flush()
                existing[name] = role

        user = User(
            username=username,
            email=f"{username}@test.local",
            hashed_password=hash_password(password),
            is_active=is_active,
            is_superuser=is_superuser,
        )
        user.roles = [existing[n] for n in role_names]
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture
def token_for(make_user) -> Callable[..., tuple[str, User]]:
    """Factory: create a user and return ``(jwt_token, user)``."""

    def _t(
        username: str = "alice",
        *,
        role_names: tuple[str, ...] = ("admin",),
        is_superuser: bool = True,
        is_active: bool = True,
        password: str = "testpass",
    ) -> tuple[str, User]:
        user = make_user(
            username,
            role_names=role_names,
            is_superuser=is_superuser,
            is_active=is_active,
            password=password,
        )
        token = create_access_token(user_id=user.id, username=user.username)
        return token, user

    return _t


@pytest.fixture
def auth_header(token_for) -> dict[str, str]:
    """Default authenticated header: a superuser admin named ``alice``.

    Tests that need a specific role or non-superuser user should call
    ``token_for`` directly.
    """
    token, _ = token_for("alice", role_names=("admin",), is_superuser=True)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def approver_header(token_for) -> dict[str, str]:
    """A second superuser admin named ``bob`` so tests that go through the
    approve-then-launch flow can use a different identity for approval —
    Separation of Duties forbids the creator from approving their own job.
    """
    token, _ = token_for("bob", role_names=("admin",), is_superuser=True)
    return {"Authorization": f"Bearer {token}"}
