# Frontend Build Plan

Step-by-step roadmap for taking the PA Platform frontend from zero to a production-ready MVP. Pairs with `FRONTEND_SPECIFICATION.md` (read its §0 amendments first — they reshape the stack and the build order).

The plan is grouped into eight phases. Stop after any phase and you have something usable; the dependencies between phases are forward-only (no late-phase work shifts earlier-phase decisions).

Backend prerequisites for this plan: the JWT auth + `/users` admin surface + AWX template-id externalization are all already shipped (78 tests green, Alembic head `0002`). The only remaining backend prep is a small dashboard summary endpoint in Phase 0.

## Phase 0 — Backend prep (~30-45 min) ✅ done

1. **`GET /api/v1/dashboard/summary`** in `app/api/routes/dashboard.py` (new file). Permission: any authenticated user. Returns:
   ```json
   {
     "assets_total": 0,
     "assets_active": 0,
     "vulns_open_by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
     "jobs_by_status": {"pending_approval": 0, "approved": 0, "running": 0, "verification_pending": 0, "verified_fixed": 0, "failed": 0, "cancelled": 0},
     "wazuh_reachable": true,
     "awx_reachable": true
   }
   ```
   Counts must respect the caller's asset scope (use `apply_asset_scope` on the asset and vulnerability queries).
   Add a smoke test in `tests/test_dashboard.py`.
   Add `/api/v1/dashboard/summary` to `tests/test_api_smoke.py::test_openapi_has_expected_paths`.

## Phase 1 — Project bootstrap (~1.5 h) ✅ done

2. `npm create vite@latest frontend -- --template react-ts`
3. Tailwind CSS install + `tailwind.config.ts` with the dark navy / slate base from spec §3.
4. shadcn/ui init (`npx shadcn@latest init`) and pull primitives: `button`, `input`, `label`, `form`, `card`, `dialog`, `dropdown-menu`, `table`, `badge`, `skeleton`, `toast`, `select`, `checkbox`, `separator`, `tabs`, `tooltip`.
5. React Router v6 install. Create `src/router/AppRouter.tsx` with placeholder routes for every path in spec §6.
6. `npm i -D openapi-typescript` and add `"gen:types": "openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts"` to `package.json`. Run it once.
7. `src/lib/apiClient.ts` — axios wrapper that reads `import.meta.env.VITE_API_BASE_URL` and reads the token *at request time* from the auth store (so token rotation later doesn't require client reconstruction). Error normalization: any `4xx` becomes `{status, detail, fieldErrors?}`.

Deliverable: blank app boots, types are generated, every primitive renders.

## Phase 2 — Auth foundation (~3 h) ✅ done

8. `src/stores/auth.ts` — Zustand store with `{token, user, permissions, status}` and actions `login`, `logout`, `bootstrap`, `setUser`. Persists `token` to `sessionStorage`.
9. `src/pages/LoginPage.tsx` — `react-hook-form` + zod schema. POST `/auth/login`, store token, GET `/auth/me`, populate user, redirect to `/`.
10. App-level `bootstrap()` — on mount with a token, GET `/auth/me`. On 401, clear and route to `/login`.
11. `src/router/ProtectedRoute.tsx` — wraps a route element; redirects to `/login` if unauthenticated. Optional `requiredPermission?: string` prop sends the user to a "no access" page if missing.
12. Axios response interceptor: any 401 from any request → clear auth store + redirect to `/login` with a "your session expired" toast.
13. `useLogout()` hook — clears the store, navigates to `/login`. (Real revocation comes with backend feature (b); this is frontend-only for now.)

Deliverable: I can log in, refresh, lose my session at expiry, and log out cleanly.

## Phase 3 — Layout & nav (~2 h) ✅ done

14. `src/components/layout/AppShell.tsx` — sidebar + top bar + content area. Collapsible sidebar on tablet width. Mobile is explicitly out of scope for the first version.
15. `src/hooks/usePermissions.ts` — `has(permission)` and `hasAny([permissions])` reading from the auth store. Use it everywhere a UI element is permission-gated.
16. Permission-aware nav: a single `NAV_ITEMS` constant with `{label, path, icon, permission?}`. The nav component filters by `usePermissions().has(item.permission)`.
17. User menu (top-right) showing `username`, primary role, "Sign out".
18. shadcn `Toaster` mounted at the app root. Wrap `apiClient` mutations in a small `useMutationWithToast` hook.

Deliverable: logged-in user sees a navigation that reflects their permissions; routes resolve to placeholder pages.

## Phase 4 — Core read pages (~6-8 h) ✅ done

19. **Assets list** (`/assets`)
    - TanStack Query hook `useAssets({limit, offset, search})`.
    - shadcn DataTable with hostname / OS badge / status / IP / last-seen / agent-version columns.
    - Search input (debounced 300 ms), pagination controls, click-row → asset detail.
20. **Asset detail** (`/assets/:assetId`)
    - Identity card + OS card + Wazuh agent card.
    - Embedded vulnerabilities subtable (`useAssetVulnerabilities(assetId)`).
    - "Create remediation" CTA gated by `remediation:create`.
21. **Vulnerabilities list** (`/vulnerabilities`)
    - Filters: severity (chips), status, CVE search, asset selector.
    - Severity-colored badges per the color map in spec §3.
    - Click-row → "Create remediation job" dialog scoped to that vuln.
22. **Remediation jobs list** (`/remediation`)
    - Status filter chips, asset filter, paginated table.
    - Status badge per the color map; AWX job id; action; creator/approver columns.
23. **Remediation job detail** (`/remediation/:jobId`)
    - Lifecycle visualization (horizontal stepper showing the seven states).
    - Action buttons: Approve / Launch / Refresh / Verify. Each visible only when the user has the right permission AND the job is in the right status.
    - Audit trail subsection — fetch `audit-logs?entity_id={jobId}` and render newest first.
24. **Create remediation job flow**
    - Modal launched from asset detail or vulns list.
    - Form (react-hook-form + zod): asset (preselected), optional vuln, action select, optional note.
    - On success, navigate to the new job's detail page.

Deliverable: every read flow from spec §8 works against real backend data.

## Phase 5 — Admin pages (~4-5 h) ✅ done

25. **Users list** (`/users`)
    - Active/inactive filter, role chips column, click-row → user detail dialog.
26. **Create/edit user dialog**
    - On create: username (required), email, password (required, ≥8), is_active, is_superuser, role multi-select.
    - On edit: same form minus username (locked); password optional.
    - Server-side 422 errors mapped back to form fields.
27. **Asset-scope sub-section** of user detail
    - List scoped assets + add (asset combobox) + remove buttons.
    - Banner when `is_superuser=true` explaining scope is bypassed.
28. **Audit logs page** (`/audit`)
    - Paginated timeline, filters: action / actor / entity_id.
    - Expandable row to show context JSON.
29. **Integrations page** (`/integrations`)
    - Wazuh card + AWX card with status pill, last-checked time, manual refresh button, error-detail expander.
30. **Sync controls** (panel on Integrations page)
    - "Sync agents" / "Sync vulnerabilities" buttons gated by `sync:run`.
    - Show summary toast on completion (created / updated / unchanged / errors).

Deliverable: an admin can fully manage users and trigger syncs via the UI.

## Phase 6 — Dashboard & polish (~3 h) ✅ done

31. **Dashboard** (`/`)
    - Stat cards (totals from `/dashboard/summary`).
    - Severity distribution bar / donut.
    - Recent vulnerabilities table (top 5).
    - Recent remediation jobs table (top 5).
    - Integration status row.
32. **Loading skeletons** — every table/card replaces its content with a shadcn `Skeleton` while loading. No spinners.
33. **Empty states** — "No vulnerabilities yet" with a contextual CTA where one exists.
34. **Error states** — TanStack Query errors render an inline error card + retry button.
35. **Form polish** — zod field-level errors visible, submit disabled during in-flight, server 422 mapped to fields.

Deliverable: enterprise-grade feel — no dead spinners, no jumping layouts, no raw stack traces in the UI.

## Phase 7 — Tests & docs (~3 h, partially done — docs only)

36. Vitest + React Testing Library + msw (Mock Service Worker) for API mocking. — *deferred*
37. Critical-path tests: — *deferred*
    - LoginPage: success → store updated, redirect.
    - LoginPage: failure → error toast, no redirect.
    - ProtectedRoute: redirects when unauthenticated.
    - usePermissions: returns the right answers from a seeded store.
    - AssetsPage: renders rows from msw-mocked response.
    - Create-user dialog: 422 from server maps to the right field.
    - Remediation job detail: button visibility matches status × permission matrix.
38. `frontend/README.md` — install, dev, env vars, codegen, tests, build, project layout. ✅ done
39. Update top-level project README (or create one) to reference both `backend/README.md` and `frontend/README.md`. ✅ done

Deliverable: green test run, a contributor can clone and run.

## Phase 8 — Production-readiness (later, optional, ~3-5 h)

40. Multi-stage `Dockerfile` for the frontend: `node` build → `nginx:alpine` serving the built assets.
41. nginx config: serve `/`, proxy `/api/v1/*` to the backend, set `Cache-Control` for hashed assets.
42. Add `frontend` service to root `docker-compose.yml`.
43. CI (GitHub Actions): typecheck, lint, vitest, build.
44. Backend CORS: tighten `CORS_ALLOW_ORIGINS` to the production domain.
45. Pair with backend feature (b) refresh tokens — once landed, swap `sessionStorage` for HttpOnly cookie + silent refresh interceptor.

## Realistic totals

| Phase | Estimate |
|---|---|
| 0 — Backend prep | 0.5-0.75 h |
| 1 — Bootstrap | 1.5 h |
| 2 — Auth | 3 h |
| 3 — Layout & nav | 2 h |
| 4 — Core read pages | 6-8 h |
| 5 — Admin pages | 4-5 h |
| 6 — Dashboard + polish | 3 h |
| 7 — Tests & docs | 3 h |
| 8 — Production (optional) | 3-5 h |
| **MVP (end of Phase 7)** | **~23-26 h** |
| **Production-ready (incl. Phase 8)** | **~26-31 h** |

A single conversation cannot finish this. Plan one phase per session, commit at each phase boundary, and update this doc with "✅ done" markers as you go.

## Resume points

Phases 0-6 were completed 2026-05-09. Phase 7 was scoped down to **docs-only** (frontend/README.md + top-level README.md ✅). The Vitest + msw + critical-path tests (steps 36-37) were deliberately deferred to keep MVP scope tight — they remain as future work.

The next session can pick up either:
- **The deferred Phase 7 tests** — useful as a regression net for the JobActions permission×status matrix and the UserDialog 422 mapping, both of which are easy to break by inspection.
- **Phase 8 (production-readiness)** — frontend Dockerfile, nginx config, frontend service in `docker-compose.yml`, GitHub Actions CI, tighten `CORS_ALLOW_ORIGINS`, and pair the sessionStorage→HttpOnly cookie swap with the deferred backend refresh-tokens work.
