# PA Platform — Backend

FastAPI service that orchestrates the **vulnerability detect → correct → verify** loop:

```
Wazuh agents → Wazuh API → THIS BACKEND → AWX → target hosts
                                ↑                      ↓
                                └──── Wazuh re-scan ───┘
```

The backend is the *only* component that talks to Wazuh, AWX, and the database. Frontends, scripts, and operators all go through `/api/v1/...` so RBAC, approval, and audit are enforced uniformly.

For the full pipeline narrative see `../flow.txt`. For the auth design see `../docs/JWT_RBAC_IMPLEMENTATION_FLOW.md`.

## Quick start

Prerequisites: Python 3.13, Docker, `docker compose` (or `docker-compose`).

```bash
# 1. From the project root, start Postgres + Redis.
cd ..
cp .env.example .env          # then fill in real values; see "Environment" below
docker compose up -d

# 2. Backend deps + migrations.
cd backend
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head

# 3. Seed the four roles + first admin (idempotent).
.venv/bin/python -m scripts.create_admin

# 4. Run.
.venv/bin/uvicorn app.main:app --reload --port 8000
```

OpenAPI / Swagger UI: <http://localhost:8000/docs>.

## Environment

`.env` lives at the project root (`../.env`). The most important keys:

| Key | Purpose |
|---|---|
| `DATABASE_URL` | Postgres URL — must match `docker-compose.yml`. |
| `JWT_SECRET` | Signing key. Rotate via `python -c "import secrets; print(secrets.token_urlsafe(64))"`. |
| `WAZUH_API_URL` / `WAZUH_API_USER` / `WAZUH_API_PASSWORD` | Wazuh Server API (port 55000). |
| `AWX_API_URL` / `AWX_API_TOKEN` (or `AWX_API_USER`+`AWX_API_PASSWORD`) | AWX REST API. |
| `AWX_TEMPLATE_PACKAGE_UPDATE` etc. | Numeric IDs of approved AWX job templates per remediation action. |
| `FIRST_ADMIN_USERNAME` / `_EMAIL` / `_PASSWORD` | Read by `scripts/create_admin.py`. |

`.env.example` documents every key.

## Project layout

```
backend/
├── alembic/                 Migrations (0001 schema, 0002 auth/rbac)
├── app/
│   ├── api/
│   │   ├── dependencies.py  get_db, get_current_user, require_permission, apply_asset_scope
│   │   ├── router.py        Aggregate of every resource router
│   │   └── routes/          One file per resource: auth, users, assets, vulnerabilities,
│   │                        sync, remediation, integrations, audit, health
│   ├── core/
│   │   ├── config.py        Pydantic Settings (env-driven, lru_cached)
│   │   ├── permissions.py   Permission enum + ROLE_PERMISSIONS mapping
│   │   └── security.py      bcrypt + PyJWT helpers
│   ├── db/                  SQLAlchemy engine + session factory
│   ├── models/              ORM: Asset, Vulnerability, RemediationJob, AuditLog, User, Role
│   ├── schemas/             Pydantic request/response shapes
│   ├── services/            Business logic: wazuh_client, ansible_client, sync_service,
│   │                        remediation_service (state machine), auth_service, user_service,
│   │                        normalizers, audit_service
│   └── main.py              FastAPI app + CORS + router mount
├── scripts/
│   └── create_admin.py      Idempotent bootstrap: 4 roles + first admin user
├── tests/                   pytest, in-memory SQLite, FakeWazuh / FakeAwx
└── requirements.txt
```

## Authentication & authorization

- **JWT** — `POST /api/v1/auth/login` exchanges username/email + password for a 60-minute access token. The token carries only identity (`sub`, `username`, `exp`); roles and permissions are resolved from the database on every request, so role changes take effect immediately rather than waiting for token expiry.
- **RBAC** — Each route declares a required permission via `require_permission(...)`. Permissions live in `app/core/permissions.py` as a `StrEnum`; the role→permissions mapping is a constant dict in the same file. Four named roles: `admin`, `security_analyst`, `remediation_operator`, `viewer`.
- **Asset scope** — Non-superusers see only assets explicitly granted in `user_asset_scopes`. `is_superuser=True` is the dedicated escape hatch and bypasses scope filtering entirely. List endpoints filter via `apply_asset_scope`; detail endpoints check via `require_asset_access`.
- **Separation of Duties** — The user who *creates* a remediation job cannot also approve it. Enforced in `remediation_service.approve_job`.
- **Audit** — Every sensitive action (login attempts, sync runs, remediation transitions, user CRUD, scope changes) writes one row to `audit_logs`. Append-only; the actor is the username from the JWT.

## Remediation lifecycle

```
pending_approval → approved → running → verification_pending → verified_fixed
                                               └→ failed / cancelled
```

Each transition is its own POST endpoint that runs the corresponding `remediation_service` function and writes an audit row. Wazuh, not AWX, has the final word — `verify` re-pulls the agent's CVE list and only marks `verified_fixed` if the (CVE, package) pair is gone.

## Running tests

```bash
.venv/bin/pytest -q
```

Tests use an in-memory SQLite engine with FK enforcement, plus `FakeWazuh` / `FakeAwx` fixtures defined in `tests/conftest.py`. No real Wazuh / AWX is required.

## Migrations

```bash
.venv/bin/alembic current                          # show current revision
.venv/bin/alembic upgrade head                     # apply pending
.venv/bin/alembic revision --autogenerate -m "…"   # diff models vs DB
.venv/bin/alembic downgrade -1                     # roll back one
```

Models are imported by `alembic/env.py` so autogenerate sees the full schema. Always review autogenerated migrations before committing — autogenerate is a starting point, not the final word.

## Health probes

| Path | Purpose | Auth |
|---|---|---|
| `GET /health` | Process is up. Safe to hit from a load balancer. | None |
| `GET /api/v1/health` | DB reachable. | Any logged-in user |
| `GET /api/v1/integrations/wazuh/health` | Wazuh reachable. | `integrations:read` |
| `GET /api/v1/integrations/ansible/health` | AWX reachable. | `integrations:read` |

## Where to find more

- `../flow.txt` — the 14-step pipeline reference.
- `../docs/JWT_RBAC_IMPLEMENTATION_FLOW.md` — auth/RBAC design and amendments.
- `../docs/AWX_ENVIRONMENT.md` — AWX setup notes for the lab.
- `../docs/PROJECT_HANDOFF_DOCUMENT.md` — broader project handoff (older; cross-check against current code).
