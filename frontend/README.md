# PA Platform — Frontend

Operator console for the **vulnerability detect → correct → verify** pipeline. React + TypeScript + Vite + Tailwind + shadcn/ui, talking only to the backend's `/api/v1` surface — never to Wazuh, AWX, or the database directly.

```
┌──────────────────────┐   ┌────────────────────────┐
│  Browser (this app)  │ → │  Backend  /api/v1/...  │ → Wazuh / AWX / Postgres
└──────────────────────┘   └────────────────────────┘
```

For the full pipeline narrative see `../flow.txt`. For the spec this implements see `../docs/FRONTEND_SPECIFICATION.md` (read its §0 amendments first).

## Quick start

Prerequisites: Node 20+, npm 9+, and the backend running at `http://localhost:8000` (see `../backend/README.md`).

```bash
# 1. Install. (.npmrc already sets legacy-peer-deps=true — see "Gotchas".)
npm install

# 2. Point at the backend.
cp .env.example .env          # then edit if your backend is elsewhere

# 3. Generate TS types from the backend's OpenAPI schema.
#    (Requires backend running; one-shot alternative below.)
npm run gen:types

# 4. Run.
npm run dev
```

App: <http://localhost:5173>. Sign in with the admin user created by `python -m scripts.create_admin` on the backend.

## Environment

`.env` lives next to `package.json`. Vite only exposes vars prefixed with `VITE_`.

| Key | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Backend origin **without** the `/api/v1` suffix. The `apiClient` adds it. Defaults to `http://localhost:8000`. |

## Scripts

```bash
npm run dev          # Vite dev server with HMR
npm run build        # tsc -b && vite build → dist/
npm run preview      # serve the built bundle
npm run typecheck    # tsc -b --noEmit (no emit, fastest CI gate)
npm run lint         # eslint .
npm run gen:types    # openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts
```

### Generating types without a running backend

`gen:types` hits the live `/openapi.json`. If the backend isn't running, dump the schema directly from the FastAPI app instead:

```bash
cd ../backend && .venv/bin/python -c "
import json, os
for k, v in {
  'DATABASE_URL': 'sqlite:///:memory:',
  'WAZUH_API_URL': 'http://x', 'WAZUH_API_USER': 'x', 'WAZUH_API_PASSWORD': 'x',
  'AWX_API_URL': 'http://x', 'AWX_API_TOKEN': 'x',
  'JWT_SECRET': 'x' * 64,
}.items():
    os.environ.setdefault(k, v)
from app.main import app
print(json.dumps(app.openapi()))
" > /tmp/openapi.json && cd ../frontend \
  && npx openapi-typescript /tmp/openapi.json -o src/types/api.ts
```

## Project layout

```
frontend/
├── public/                          Static assets served as-is by Vite
├── src/
│   ├── api/                         Typed thin wrappers around apiClient
│   │   ├── types.ts                 Re-exports of backend schemas + canonical literal arrays
│   │   ├── assets.ts vulnerabilities.ts remediation.ts audit.ts
│   │   ├── users.ts sync.ts integrations.ts dashboard.ts
│   ├── components/
│   │   ├── ui/                      shadcn/ui primitives (copied in, not a dependency)
│   │   ├── layout/                  AppShell, SideNav, UserMenu, PageHeader, navItems
│   │   ├── data/                    DataTable<T>, Pagination
│   │   ├── feedback/                EmptyState, ErrorState
│   │   ├── badges/                  SeverityBadge, JobStatusBadge, AssetStatusBadge
│   │   ├── dashboard/               StatCard, SeverityDistribution
│   │   ├── remediation/             CreateJobDialog, LifecycleStepper, JobActions, JobAuditTrail
│   │   ├── users/                   UserDialog, UserDetailDialog, AssetScopeSection
│   │   ├── integrations/            IntegrationCard, SyncControls
│   │   └── assets/                  AssetCombobox (server-side search)
│   ├── hooks/
│   │   ├── queries/                 TanStack Query wrappers, one per resource
│   │   ├── usePermissions.ts        has(p) / hasAny(ps) — superuser bypass mirrors the backend
│   │   ├── useMutationWithToast.ts  TQ mutation wrapper; suppresses toast on 422-with-fields and 401
│   │   ├── useDebouncedValue.ts     300 ms debounce for search inputs
│   │   ├── useAuthBootstrap.ts      App-mount /auth/me hydration
│   │   ├── useNavigatorRegistration.ts  hand React Router's navigate to apiClient
│   │   └── useLogout.ts             clear store + navigate /login
│   ├── lib/
│   │   ├── apiClient.ts             axios instance, request-time bearer, 401 → clear+redirect
│   │   ├── navigation.ts            registerNavigator/navigateTo registry
│   │   ├── queryClient.ts           QueryClient defaults (30s staleTime, no-retry on 4xx)
│   │   ├── format.ts                formatDateTime, formatRelative, dash null fallback
│   │   └── utils.ts                 cn() — class-name merger
│   ├── pages/                       One file per route in spec §6
│   ├── router/                      AppRouter, ProtectedRoute
│   ├── stores/
│   │   └── auth.ts                  Zustand: {token,user,permissions,status}; token in sessionStorage
│   ├── types/
│   │   └── api.ts                   Generated by openapi-typescript — do not edit
│   ├── App.tsx                      QueryClientProvider + AppRouter + Toaster
│   ├── main.tsx                     React 19 createRoot
│   └── index.css                    Tailwind directives + shadcn HSL tokens (dark navy/slate)
├── components.json                  shadcn config
├── tailwind.config.ts               status palette (spec §3) + shadcn token bridge
├── vite.config.ts                   @/ alias, react plugin
├── tsconfig.json + .app + .node
└── .npmrc                           legacy-peer-deps=true (see Gotchas)
```

## Auth model

- **Login** — `POST /auth/login` returns `{access_token, ...}`. The page stages the token via `setToken` so the request interceptor can attach it on the immediately-following `GET /auth/me`. The full `setSession(token, user)` runs after `/auth/me` resolves.
- **Token storage** — `sessionStorage["pa.auth.token"]` (per spec §0 amendment 6 — smaller XSS surface than localStorage; dies with the tab). The Zustand store is the single source of truth; `apiClient` reads via `useAuthStore.getState().token` at request time so token rotation needs no client reconstruction.
- **Bootstrap** — `useAuthBootstrap` runs once on mount. Token in storage → call `/auth/me` and hydrate. No token → `unauthenticated`. Status flow: `idle → authenticating → authenticated | unauthenticated`. `ProtectedRoute` renders a skeleton during `idle`/`authenticating` so a refresh doesn't flash `/login`.
- **401 from any request** — interceptor clears the store, toasts "your session expired", and SPA-navigates to `/login` (via the `src/lib/navigation.ts` registry, since the interceptor has no router context). Skipped for `/auth/login` itself, where 401 means "bad credentials" and the LoginPage owns the UX.
- **Permission gating** — `usePermissions().has("...")` reads from the store. Used in nav (`NAV_ITEMS[i].permission`), per-button gates (`<JobActions>`, "Create remediation" CTA), and `<ProtectedRoute requiredPermission="users:manage">`. Backend remains the security control; this is UX only.

## State machine: remediation jobs

The frontend mirrors the backend's lifecycle. The `<LifecycleStepper>` renders the 5-step happy path; `failed` and `cancelled` collapse to a terminal pill so you don't see "all dots dark":

```
pending_approval → approved → running → verification_pending → verified_fixed
                                                └→ failed / cancelled
```

`<JobActions>` shows each transition button only when the user has the right permission **and** the job is in the right status. The matrix lives in one place — `src/components/remediation/JobActions.tsx`:

| Action  | Permission             | Required status        |
|---------|------------------------|------------------------|
| Approve | `remediation:approve`  | `pending_approval`     |
| Launch  | `remediation:launch`   | `approved`             |
| Refresh | `remediation:launch`   | `running`              |
| Verify  | `remediation:verify`   | `verification_pending` |

## Adding things

- **A new page** — add a file under `src/pages/`, register the route in `src/router/AppRouter.tsx`, add an entry to `NAV_ITEMS` in `src/components/layout/navItems.ts` (with the right `permission`).
- **A new resource** — add `src/api/<resource>.ts` (typed wrapper over `apiClient`), then a TQ wrapper under `src/hooks/queries/`. Mirror the existing `assets.ts` / `useAssets.ts` shape.
- **A new mutation with toast** — wrap with `useMutationWithToast`. Pass `successMessage` (string or function) and let the wrapper handle errors. Don't toast 422 yourself — the wrapper suppresses on 422-with-fieldErrors so `react-hook-form.setError` can take over.
- **A new shadcn primitive** — `npx shadcn@latest add <name> --yes` (works thanks to `.npmrc`).

## Gotchas

- **`.npmrc` sets `legacy-peer-deps=true`.** The Vite 8 scaffold pulled TypeScript 6, but several packages (`openapi-typescript`, `axios`, eslint plugins) still declare `typescript@^5` peers. The mismatch is harmless — those packages only emit/consume types — but strict resolution refuses to install. Don't delete the `.npmrc`.
- **TanStack Query v5 callback signatures changed.** `MutateOptions.onSuccess` / `onError` take `(data, variables, onMutateResult, context)` — four args. `useMutationWithToast` already matches; if you copy-paste from older TQ examples you'll get a TS error.
- **`gen:types` overwrites `src/types/api.ts`.** Don't edit that file by hand; it's generated. Re-run after every backend schema change.
- **Don't talk to Wazuh or AWX from the browser.** Hard rule from the security report — every call goes through the backend so RBAC, asset scope, and audit are enforced uniformly.

## Where to find more

- `../docs/FRONTEND_SPECIFICATION.md` — what this app is supposed to be. Read the §0 amendments.
- `../docs/FRONTEND_BUILD_PLAN.md` — the 8-phase build plan; each phase has a ✅ marker.
- `../backend/README.md` — backend setup, RBAC model, env vars.
- `../flow.txt` — the 14-step pipeline reference.
