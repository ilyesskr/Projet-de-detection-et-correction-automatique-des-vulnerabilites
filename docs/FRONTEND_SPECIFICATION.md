# Frontend Specification

This document explains how the frontend should be designed and implemented for the PA Detection & Correction platform.

The frontend is the enterprise user interface that allows security teams to view assets, vulnerabilities, remediation jobs, users, audit logs, and integration health.

## 0. Amendments (2026-05-09)

Six amendments to the original spec. Read the rest of this document with these in mind. The phased build order with time estimates lives in `FRONTEND_BUILD_PLAN.md`.

1. **Use shadcn/ui on top of Tailwind, not Tailwind alone.** Building accessible tables, dialogs, dropdowns, popovers, comboboxes from raw Tailwind is weeks of avoidable work. shadcn/ui = Radix primitives (a11y, keyboard nav) + Tailwind styling, copy-pasted into the repo (no library lock-in). Matches §3's "professional / structured / trustworthy" visual direction by default.

2. **Generate TypeScript types from the backend's OpenAPI schema.** Run `openapi-typescript` against `/openapi.json` to produce `src/types/api.ts` and add a `gen:types` npm script. Without this, every backend response shape change silently breaks the frontend until the page is clicked. With it, `tsc` catches drift at compile time.

3. **Add `GET /api/v1/dashboard/summary` to the backend before building the dashboard.** The original spec hedges that the frontend can compute totals from list endpoints if no summary endpoint exists — that means 5-8 round trips per dashboard load. A small backend addition returning `{assets_total, assets_active, vulns_open_by_severity, jobs_by_status, wazuh_ok, awx_ok}` makes the dashboard one query.

4. **Use `react-hook-form` + `zod` for every form.** Login, create-user, edit-user, create-remediation-job all need validated forms. Without a library, you hand-wire onChange/error state for every field. `zod` schemas double as TypeScript types and as the validation source of truth.

5. **Treat login + protected routing + `/auth/me` + auth context as one inseparable step.** The original spec lists them as build steps 5-8. They cannot be tested independently and should be implemented as a single block.

6. **Token storage: `sessionStorage`, not `localStorage`.** Smaller XSS surface, and the "session ends when the tab closes" semantic is honest given access tokens are 60 minutes long. Revisit when refresh tokens land on the backend (deferred per the JWT_RBAC plan amendment 6).

Stack confirmed: React + TypeScript + Vite + Tailwind CSS + **shadcn/ui** + React Router + TanStack Query + axios + **react-hook-form + zod** + **openapi-typescript** + Vitest + React Testing Library.

## 1. Frontend Objective

The frontend must provide a professional web interface for:

```text
Logging in securely
Viewing synchronized Wazuh assets
Viewing vulnerabilities
Creating and tracking remediation jobs
Managing users, roles, and asset scopes
Viewing audit logs
Checking Wazuh and AWX integration health
Triggering Wazuh sync operations
```

The frontend must never communicate directly with Wazuh or AWX.

All communication must go through the backend API.

## 2. Recommended Stack

Use:

```text
React
TypeScript
Vite
React Router
TanStack Query
Tailwind CSS
Axios or a typed fetch wrapper
```

Reasons:

```text
React gives a flexible component model.
TypeScript reduces API integration mistakes.
Vite provides fast development.
React Router handles protected pages.
TanStack Query handles API caching, loading states, errors, and refetching.
Tailwind CSS allows a fast but polished enterprise UI.
```

## 3. Visual Direction

The frontend should look like an enterprise security operations platform.

It should feel:

```text
Professional
Clear
Structured
Trustworthy
Modern
Operational
```

Avoid:

```text
Generic purple SaaS design
Toy-like dashboards
Overloaded screens
Unclear action buttons
Excessive animations
Uncontrolled colors
```

Suggested visual identity:

```text
Dark navy / slate base
Light content cards
Clear status colors
Sharp typography
Strong tables
Compact filters
Readable badges
Enterprise dashboard layout
```

Suggested status colors:

```text
Critical: red
High: orange
Medium: amber
Low: blue
Fixed: green
Failed: red
Running: blue
Pending approval: amber
Approved: cyan
```

## 4. Backend API Base

The frontend should read the backend API URL from an environment variable:

```env
VITE_API_BASE_URL=http://localhost:8000
```

All API requests should be made to:

```text
{VITE_API_BASE_URL}/api/v1/...
```

Examples:

```text
POST /api/v1/auth/login
GET  /api/v1/auth/me
GET  /api/v1/assets
GET  /api/v1/vulnerabilities
GET  /api/v1/remediation/jobs
```

## 5. Authentication Flow

### Login

The login page sends:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

Body:

```json
{
  "username": "admin",
  "password": "password"
}
```

Response:

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

The frontend stores the access token.

For the current version, storing it in memory or local storage is acceptable for development.

For production, prefer a more secure session strategy when refresh tokens are implemented.

### Authenticated Requests

Every protected request must include:

```http
Authorization: Bearer <access_token>
```

### Current User

After login, call:

```http
GET /api/v1/auth/me
```

This returns:

```text
User identity
Roles
Permissions
is_superuser
```

The frontend should use this response to decide which pages and buttons to show.

The frontend should not hardcode role behavior.

It should check permissions.

Example:

```text
Show users page only if permissions contains "users:manage".
Show remediation approve button only if permissions contains "remediation:approve".
```

## 6. Protected Routing

The frontend should have protected routes.

If the user is not logged in:

```text
Redirect to /login
```

If the user is logged in but lacks permission:

```text
Show "Access denied"
```

Suggested route structure:

```text
/login
/dashboard
/assets
/assets/:assetId
/vulnerabilities
/remediation
/remediation/:jobId
/users
/audit
/integrations
```

## 7. API Client

Create one centralized API client.

Suggested file:

```text
src/lib/api.ts
```

Responsibilities:

```text
Read VITE_API_BASE_URL
Attach Authorization header
Parse JSON responses
Handle 401 responses
Handle API errors consistently
Expose typed functions
```

Example API modules:

```text
src/api/auth.ts
src/api/assets.ts
src/api/vulnerabilities.ts
src/api/remediation.ts
src/api/users.ts
src/api/audit.ts
src/api/integrations.ts
src/api/sync.ts
```

## 8. Main Pages

## 8.1 Login Page

Purpose:

```text
Authenticate the user and create a frontend session.
```

Elements:

```text
Platform logo/name
Username input
Password input
Login button
Error message for invalid credentials
Loading state
```

Behavior:

```text
On success, store token and redirect to /dashboard.
On failure, show a clear error.
```

## 8.2 Dashboard Page

Purpose:

```text
Show a high-level security overview.
```

Suggested cards:

```text
Total assets
Active assets
Open vulnerabilities
Critical vulnerabilities
High vulnerabilities
Pending remediation jobs
Running remediation jobs
Failed remediation jobs
Wazuh status
AWX status
```

Suggested sections:

```text
Severity distribution
Recent vulnerabilities
Recent remediation jobs
Integration health
```

If backend summary endpoints do not exist yet, the frontend can initially compute totals from list endpoints.

## 8.3 Assets Page

Endpoint:

```http
GET /api/v1/assets
```

Features:

```text
Table of assets
Search by hostname
Pagination
Status badge
OS badge
Agent version
IP address
Last seen
Click row to open asset details
```

Important fields:

```text
id
wazuh_agent_id
hostname
ip_address
os_name
os_version
os_platform
agent_version
status
last_seen
```

## 8.4 Asset Detail Page

Endpoints:

```http
GET /api/v1/assets/{asset_id}
GET /api/v1/assets/{asset_id}/vulnerabilities
```

Features:

```text
Asset identity panel
OS information
Wazuh agent status
List of vulnerabilities for this asset
Button to create remediation job for a vulnerability
```

## 8.5 Vulnerabilities Page

Endpoint:

```http
GET /api/v1/vulnerabilities
```

Supported filters:

```text
asset_id
severity
status
cve
limit
offset
```

Features:

```text
Table of vulnerabilities
Severity badges
CVE search
Package name
Installed version
Fixed version
Status
Create remediation action
```

Important fields:

```text
id
asset_id
cve
title
severity
cvss_score
package_name
installed_version
fixed_version
published_at
status
```

## 8.6 Remediation Jobs Page

Endpoint:

```http
GET /api/v1/remediation/jobs
```

Features:

```text
List remediation jobs
Filter by status
Filter by asset
Show lifecycle status
Show AWX job id
Show action
Show creator and approver
Open job details
```

Status flow:

```text
pending_approval
approved
running
verification_pending
verified_fixed
failed
cancelled
```

Action buttons:

```text
Approve
Launch
Refresh
Verify
```

Button visibility should be permission-based:

```text
remediation:approve -> Approve
remediation:launch  -> Launch / Refresh
remediation:verify  -> Verify
```

The frontend should also respect status:

```text
Only pending_approval jobs can be approved.
Only approved jobs can be launched.
Only running jobs can be refreshed.
Only verification_pending jobs can be verified.
```

## 8.7 Create Remediation Job Flow

Endpoint:

```http
POST /api/v1/remediation/jobs
```

Body:

```json
{
  "asset_id": "...",
  "vulnerability_id": "...",
  "action": "package_update",
  "note": "Update vulnerable package"
}
```

Important:

```text
The frontend must not send created_by.
The backend derives created_by from the JWT user.
```

Available actions:

```text
package_update
windows_update
service_restart
config_change
```

## 8.8 Users Admin Page

Visible only if:

```text
permissions contains "users:manage"
```

Endpoints:

```http
GET    /api/v1/roles
GET    /api/v1/users
POST   /api/v1/users
GET    /api/v1/users/{user_id}
PATCH  /api/v1/users/{user_id}
DELETE /api/v1/users/{user_id}
GET    /api/v1/users/{user_id}/asset-scopes
POST   /api/v1/users/{user_id}/asset-scopes
DELETE /api/v1/users/{user_id}/asset-scopes/{asset_id}
```

Features:

```text
List users
Create user
Edit email
Activate/deactivate user
Reset password
Assign roles
Set is_superuser
Assign asset scopes
Delete user
```

Important:

```text
Do not show hashed_password.
Do not allow the frontend to send hashed_password.
Show a warning before deleting users.
Explain that superusers bypass asset scope.
```

## 8.9 Audit Logs Page

Endpoint:

```http
GET /api/v1/audit-logs
```

Filters:

```text
action
actor
entity_id
limit
offset
```

Features:

```text
Audit timeline
Actor
Action
Entity type
Entity id
Success/failure
Context JSON viewer
Timestamp
```

## 8.10 Integrations Page

Endpoints:

```http
GET /api/v1/integrations/wazuh/health
GET /api/v1/integrations/ansible/health
```

Features:

```text
Wazuh connection status
AWX connection status
Last checked time
Refresh button
Error details
```

## 8.11 Sync Page Or Sync Controls

Endpoints:

```http
POST /api/v1/sync/wazuh/agents
POST /api/v1/sync/wazuh/vulnerabilities
```

Visible only if:

```text
permissions contains "sync:run"
```

Features:

```text
Sync agents button
Sync vulnerabilities button
Show result summary
Show errors if any
Disable button while syncing
```

## 9. Permissions And UI Behavior

The frontend should use permissions from:

```http
GET /api/v1/auth/me
```

Permission-driven UI:

```text
assets:read              -> show assets page
vulnerabilities:read     -> show vulnerabilities page
integrations:read        -> show integrations page
audit:read               -> show audit logs page
sync:run                 -> show sync controls
remediation:read         -> show remediation page
remediation:create       -> show create remediation button
remediation:approve      -> show approve button
remediation:launch       -> show launch / refresh buttons
remediation:verify       -> show verify button
users:manage             -> show users admin page
```

Important:

```text
Frontend permissions improve UX only.
Backend permissions remain the real security control.
```

## 10. Error Handling

The frontend should handle:

```text
401 Unauthorized -> redirect to login
403 Forbidden -> show access denied
404 Not Found -> show not found message
409 Conflict -> show conflict message
422 Validation Error -> show field-level errors
502 Bad Gateway -> show integration/backend dependency failure
500 Server Error -> show generic error
```

Error messages should be clear but not expose secrets.

## 11. Loading States

Every async operation should have:

```text
Loading state
Success state
Error state
Empty state
```

Examples:

```text
Assets table loading skeleton
No vulnerabilities found empty state
Remediation launch in progress state
Integration check failed state
```

## 12. Frontend Project Structure

Suggested structure:

```text
frontend/
├── src/
│   ├── api/
│   │   ├── auth.ts
│   │   ├── assets.ts
│   │   ├── vulnerabilities.ts
│   │   ├── remediation.ts
│   │   ├── users.ts
│   │   ├── audit.ts
│   │   ├── integrations.ts
│   │   └── sync.ts
│   ├── components/
│   │   ├── layout/
│   │   ├── tables/
│   │   ├── forms/
│   │   ├── badges/
│   │   └── feedback/
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   └── usePermissions.ts
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── AssetsPage.tsx
│   │   ├── AssetDetailPage.tsx
│   │   ├── VulnerabilitiesPage.tsx
│   │   ├── RemediationPage.tsx
│   │   ├── UsersPage.tsx
│   │   ├── AuditPage.tsx
│   │   └── IntegrationsPage.tsx
│   ├── router/
│   │   └── AppRouter.tsx
│   ├── types/
│   │   └── api.ts
│   ├── lib/
│   │   ├── apiClient.ts
│   │   └── formatting.ts
│   ├── App.tsx
│   └── main.tsx
├── .env.example
├── package.json
└── vite.config.ts
```

## 13. Implementation Order

Build in this order:

```text
1. Create React + TypeScript + Vite project.
2. Add Tailwind CSS and base design tokens.
3. Create API client with Authorization header support.
4. Create auth store/hook.
5. Build login page.
6. Build protected route wrapper.
7. Build main dashboard layout.
8. Connect /auth/me.
9. Build assets page.
10. Build vulnerabilities page.
11. Build remediation jobs page.
12. Build users admin page.
13. Build audit logs page.
14. Build integrations page.
15. Add sync controls.
16. Polish loading, errors, empty states, badges, and responsiveness.
```

## 14. Manual Test Flow

After the frontend is created, manually test:

```text
Login with admin user
Open dashboard
Call /auth/me
View assets
Run Wazuh agent sync
Run vulnerability sync
View vulnerabilities
Create remediation job
Approve remediation job using another user
Launch remediation job
Refresh remediation job
Verify remediation job
Create a new user
Assign role
Assign asset scope
Log in as scoped user
Confirm scoped user sees only assigned assets
Open audit logs
Check integration health
```

## 15. Production Notes

Before production:

```text
Use HTTPS
Avoid storing long-lived tokens in localStorage
Add refresh tokens and logout revocation
Protect against XSS
Use secure cookies when refresh tokens are implemented
Add frontend error logging
Add strict CORS origins
Use environment-specific API base URLs
```

Refresh tokens and logout revocation are deferred until the frontend login flow exists.

They are not required for the first frontend version.
