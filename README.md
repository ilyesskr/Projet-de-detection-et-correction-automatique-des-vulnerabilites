# PA Platform — Vulnerability Detection & Remediation

Enterprise console for closing the loop between **Wazuh detection** and **Ansible AWX remediation**, with RBAC, asset scope, approval workflow, and an append-only audit trail in front of every sensitive action.

```
┌─────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────┐    ┌──────────────┐
│ Wazuh   │ →  │ Wazuh API   │ →  │ FastAPI      │ →  │ AWX     │ →  │ Target hosts │
│ agents  │    │ + Indexer   │    │ (this repo)  │    │ (Ansible)│   │ (patched)    │
└─────────┘    └─────────────┘    └──────────────┘    └─────────┘    └──────────────┘
                                       ↑                                    │
                                       └────────── Wazuh re-scan ───────────┘
```

The FastAPI backend is the **only** component that talks to Wazuh, AWX, and Postgres. The React frontend, scripts, and operators all go through `/api/v1/...` so RBAC, approval, and audit are enforced uniformly. AWX runs only **approved** job templates — never arbitrary playbooks or shell — and Wazuh re-verification, not AWX's own job status, is the source of truth for "is the CVE actually fixed."

For the 14-step pipeline narrative see [`flow.txt`](./flow.txt).

## Repo layout

```
PA_DETECTION_CORRECTION/
├── backend/              FastAPI service — orchestration, RBAC, audit, AWX/Wazuh clients
│   └── README.md         ← start here for backend setup
├── frontend/             React + TS + Vite operator console
│   └── README.md         ← start here for frontend setup
├── docs/                 Specs, design notes, slides
│   ├── FRONTEND_SPECIFICATION.md       What the frontend is supposed to be
│   ├── FRONTEND_BUILD_PLAN.md          8-phase build plan with ✅ markers
│   ├── JWT_RBAC_IMPLEMENTATION_FLOW.md Auth design + amendments
│   ├── AWX_ENVIRONMENT.md              AWX setup notes for the lab
│   ├── PROJECT_HANDOFF_DOCUMENT.md     Older project handoff (cross-check vs current code)
│   ├── enterprise_security_architecture_report.pdf
│   ├── project_architecture_diagram.pdf
│   └── …                               Slides
├── docker-compose.yml    Postgres + Redis (the data plane)
├── flow.txt              The 14-step pipeline reference
├── .env.example          Documents every env key the backend reads
└── .gitignore
```

## Quick start (full stack)

Prerequisites: Docker + `docker compose`, Python 3.13, Node 20+, npm 9+. A reachable Wazuh Manager (port 55000) and AWX instance for the real flows; the backend test suite uses fakes and needs neither.

```bash
# 1. Data plane — Postgres + Redis.
cp .env.example .env          # then edit; see backend/README.md → "Environment"
docker compose up -d

# 2. Backend.
cd backend
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m scripts.create_admin     # idempotent: 4 roles + first admin
.venv/bin/uvicorn app.main:app --reload --port 8000

# 3. Frontend (in another shell).
cd ../frontend
npm install                                   # .npmrc handles peer-deps
cp .env.example .env                          # default points at http://localhost:8000
npm run gen:types                             # one-shot OpenAPI → TS codegen
npm run dev                                   # http://localhost:5173
```

## Component READMEs

- [`backend/README.md`](./backend/README.md) — FastAPI setup, RBAC model, env vars, migrations, tests, health probes.
- [`frontend/README.md`](./frontend/README.md) — React app setup, project layout, auth model, JobActions matrix, gotchas.

## Status

- **Backend**: feature-complete, 84 tests green, Alembic head `0002`. Implements the orchestration pipeline (flow.txt steps 7–11 and 14), JWT auth + RBAC + asset scope + Separation of Duties, /users CRUD + asset-scope management, externalized AWX template IDs, full audit trail, and a `GET /api/v1/dashboard/summary` aggregate.
- **Frontend**: every page from `docs/FRONTEND_SPECIFICATION.md` §8 is real and wired to the backend. 

## Hard rules

These are repeated from the security report and the spec. They constrain every change:

- The frontend never talks to Wazuh, AWX, or the database directly. Every action goes through the backend's `/api/v1` so RBAC, asset scope, and audit are enforced in one place.
- AWX runs only the **approved** job templates registered in `AWX_TEMPLATE_*` env vars. No arbitrary playbooks or shell — this is the security boundary, not a hint.
- Every state-changing remediation transition writes an audit row. The actor is the JWT username; the frontend cannot spoof `created_by` / `approved_by`.
- Wazuh, not AWX, decides whether a CVE is fixed. AWX returning "successful" only flips the job to `verification_pending`; `verified_fixed` requires the CVE to be absent on Wazuh's next read.

