# JWT Auth + RBAC Implementation Flow

This document defines the implementation plan for adding JWT authentication and Role-Based Access Control (RBAC) to the backend.

The goal is to replace the temporary API-key gate with a real enterprise-grade security layer based on users, roles, permissions, asset scope, auditability, and approval governance.

## 0. Amendments (2026-05-09)

Seven amendments to the original plan, applied throughout the rest of this document. Read the rest of the plan with these in mind.

1. **Permissions are an enum, not a database table.** The set of permissions is fixed and code-defined, so we do not need a `permissions` table or a `role_permissions` join table. Drop both. Permissions live in `app/core/permissions.py` as a `Permission(str, Enum)`. The role→permissions mapping is a constant dict in the same file. The `roles` table only stores the four named roles. This drops two tables, removes a class of typo bugs (`"asset:read"` vs `"assets:read"`), and gives us autocomplete in the IDE.

2. **JWT payload stays minimal.** The token carries only `sub`, `username`, and `exp`. Roles and permissions are loaded from the database on each request inside `get_current_user`. This avoids stale-permission bugs after a role change, at the cost of one extra small query per request (acceptable, and easy to cache later if needed).

3. **`require_any_permission` is a first-class dependency.** Some routes need OR-of-permissions (e.g. `GET /remediation/jobs` needs `create OR approve OR launch`). We provide both `require_permission(name)` and `require_any_permission([...])`, plus a single new `remediation:read` permission granted to all three remediation roles to keep route declarations short.

4. **Asset scope filters list endpoints, not just gates detail endpoints.** Single-asset routes (`GET /assets/{id}`) check scope and 403 on mismatch. List routes (`GET /assets`, `GET /vulnerabilities`, `GET /remediation/jobs`) silently filter their query by the user's scope. A single helper `apply_asset_scope(stmt, user, model)` is called inside every list endpoint.

5. **`is_superuser` is the only scope bypass.** The `admin` role is just "all permissions, no scope bypass." Setting `is_superuser=True` on a user is the dedicated escape hatch and is the only mechanism that skips asset-scope filtering. The two flags are independent.

6. **Refresh tokens are out of scope.** With 60-minute access tokens and no refresh, frontends will need to re-login hourly. We accept that for v1 and revisit when a frontend exists. `/auth/logout` is also deferred (stateless JWT means logout is a frontend-side token discard until we add a Redis denylist).

7. **Steps 13 and 14 of the implementation order merge.** Once the `current_user` dependency is in place, swapping `require_api_key` for permission deps and pulling `created_by`/`approved_by` from the token are part of the same edit, not separate steps.

Microsoft Graph / Intune integration is also out of scope for this project (separate decision, recorded in memory).

## 1. Objective

The backend currently uses a temporary `X-API-Key` protection mechanism.

That is acceptable during early development, but it is not enough for an enterprise platform because it does not answer these questions:

```text
Who is the user?
What is this user allowed to do?
Which assets can this user access?
Who requested a remediation?
Who approved a remediation?
Can one person both request and approve the same sensitive action?
```

The JWT + RBAC subsystem solves this by introducing:

```text
Users
Roles
Permissions
Asset scopes
JWT login tokens
Route-level authorization
Separation of Duties for remediation approval
Auditable user actions
```

## 2. Security Concepts

### User

A user represents a person who can log in to the platform.

Example:

```text
username: ilyass
email: ilyass@example.com
roles: admin, security_analyst
```

### Role

A role groups permissions under a clear responsibility.

Initial roles:

```text
admin
security_analyst
remediation_operator
viewer
```

### Permission

A permission is a precise action that can be granted or denied.

Initial permissions:

```text
assets:read
vulnerabilities:read
sync:run
remediation:create
remediation:approve
remediation:launch
remediation:verify
audit:read
integrations:read
users:manage
```

### Asset Scope

Asset scope controls which machines a user can access.

Example:

```text
User A can see all assets.
User B can only see assets assigned to him.
```

Administrators and superusers can bypass asset scope.

### JWT Token

A JWT token is issued after login.

The frontend sends it with every protected request:

```http
Authorization: Bearer <access_token>
```

The backend verifies the token and identifies the current user.

## 3. Database Models 
```text
users
roles
permissions
user_roles
role_permissions
user_asset_scopes
```

### users

fields:

```text
id
email
username
hashed_password
is_active
is_superuser
created_at
updated_at
```

Purpose:

```text
Stores platform users and their password hashes.
```

### roles

fields:

```text
id
name
description
created_at
updated_at
```

Purpose:

```text
Stores named responsibilities such as admin, viewer, or remediation_operator.
```

### permissions

fields:

```text
id
name
description
created_at
updated_at
```

Purpose:

```text
Stores precise actions such as remediation:approve or assets:read.
```

### user_roles
fields:

```text
user_id
role_id
```

Purpose:

```text
Assigns roles to users.
```

### role_permissions
fields:

```text
role_id
permission_id
```

Purpose:

```text
Assigns permissions to roles.
```

### user_asset_scopes

fields:

```text
user_id
asset_id
```

Purpose:

```text
Restricts a user to specific assets.
```

## 4. Alembic Migration

After adding the models, generate a migration:

```bash
cd /home/ilyass/Desktop/PA_DETECTION_CORRECTION/backend
.venv/bin/alembic revision --autogenerate -m "add auth rbac"
```

Review the generated migration carefully.

Then apply it:

```bash
.venv/bin/alembic upgrade head
```

Verify:

```bash
.venv/bin/alembic current
```

Expected:

```text
latest revision is applied
```

## 5. Password Hashing

Passwords must never be stored in plain text.

Add password helpers in `app/core/security.py`:

```text
hash_password(password)
verify_password(plain_password, hashed_password)
```

Use:

```text
bcrypt
```

Behavior:

```text
When a user is created, hash the password.
When a user logs in, compare the submitted password with the stored hash.
```

## 6. JWT Utilities

Add JWT helpers in `app/core/security.py`:

```text
create_access_token(user)
decode_access_token(token)
```

JWT payload should include:

```json
{
  "sub": "user_id",
  "username": "ilyass",
  "roles": ["admin"],
  "permissions": ["assets:read", "remediation:create"],
  "exp": "expiration timestamp"
}
```

The JWT secret and expiration are already configured in `.env`:

```env
JWT_SECRET=...
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
```

## 7. Auth Schemas

Add schemas for authentication and user management.

files:

```text
app/schemas/auth.py
app/schemas/user.py
```

schemas:

```text
LoginRequest
TokenResponse
TokenPayload
UserCreate
UserRead
RoleRead
PermissionRead
```

Login response:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

## 8. Auth Service

Add:

```text
app/services/auth_service.py
```

Responsibilities:

```text
Find user by username or email
Verify password
Create JWT token
Load user roles
Load user permissions
Create first admin user
Check whether user is active
```

Important rule:

```text
Inactive users must not be allowed to log in.
```

## 9. Auth Dependencies

Add dependencies used by routes:

```text
get_current_user()
require_permission(permission_name)
require_role(role_name)
require_asset_access(asset_id)
```

file:

```text
app/api/dependencies.py
```

Example usage:

```python
@router.get("/assets")
def list_assets(current_user = Depends(require_permission("assets:read"))):
    ...
```

Behavior:

```text
Missing token -> 401 Unauthorized
Invalid token -> 401 Unauthorized
Valid token but missing permission -> 403 Forbidden
Valid token but outside asset scope -> 403 Forbidden
```

## 10. Auth Routes

Add:

```text
app/api/routes/auth.py
```

Initial endpoints:

```text
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

Optional later:

```text
POST /api/v1/auth/logout
POST /api/v1/users
GET  /api/v1/users
GET  /api/v1/roles
GET  /api/v1/permissions
```

Login flow:

```text
Frontend sends username/email + password
Backend verifies credentials
Backend creates JWT
Frontend stores JWT safely
Frontend sends JWT in Authorization header
```

## 11. Route Protection Plan

permissions per route:

```text
GET  /assets                         -> assets:read
GET  /assets/{id}                    -> assets:read + asset scope
GET  /assets/{id}/vulnerabilities    -> vulnerabilities:read + asset scope

GET  /vulnerabilities                -> vulnerabilities:read

POST /sync/wazuh/agents              -> sync:run
POST /sync/wazuh/vulnerabilities     -> sync:run

GET  /integrations/wazuh/health      -> integrations:read
GET  /integrations/ansible/health    -> integrations:read

POST /remediation/jobs               -> remediation:create
GET  /remediation/jobs               -> remediation:create or remediation:approve or remediation:launch
GET  /remediation/jobs/{id}          -> remediation:create or remediation:approve or remediation:launch
POST /remediation/jobs/{id}/approve  -> remediation:approve
POST /remediation/jobs/{id}/launch   -> remediation:launch
POST /remediation/jobs/{id}/refresh  -> remediation:launch
POST /remediation/jobs/{id}/verify   -> remediation:verify

GET  /audit-logs                     -> audit:read
```

## 12. Refactor Remediation Identity

Currently, request bodies may include:

```text
created_by
approved_by
```

This is not secure because the frontend can fake those values.

After JWT auth:

```text
created_by = current_user.username
approved_by = current_user.username
```

The frontend must not decide who created or approved a remediation.

## 13. Separation of Duties

Add a hard rule:

```text
The user who created a remediation job cannot approve the same job.
```

Example:

```text
User ilyass creates remediation job A.
User ilyass tries to approve remediation job A.
Backend rejects with 403 Forbidden.
Another authorized user must approve it.
```

This protects the approval workflow and makes the platform more suitable for enterprise governance.

## 14. Bootstrap First Admin

Before users can log in, the platform needs a first admin account.

```text
scripts/create_admin.py
```

This script should:

```text
Read admin username/email/password from environment variables
Create default permissions
Create default roles
Assign all permissions to admin
Create first admin user
Assign admin role to first admin user
```

environment variables:

```env
FIRST_ADMIN_USERNAME=admin
FIRST_ADMIN_EMAIL=admin@example.com
FIRST_ADMIN_PASSWORD=change-me
```

The script should be safe to run multiple times.

If the admin already exists, it should not create duplicates.

## 15. Audit Integration

Every sensitive action should create an audit log.

Examples:

```text
auth.login.success
auth.login.failed
user.created
sync.wazuh.agents
sync.wazuh.vulnerabilities
remediation.job.created
remediation.job.approved
remediation.job.launched
remediation.job.verified
```

Audit records should include:

```text
actor
action
entity_type
entity_id
success
context
```


## 16. Acceptance Criteria

The JWT + RBAC subsystem is complete when:

```text
Users can log in and receive a JWT.
Protected routes reject missing or invalid JWTs.
Routes enforce permissions.
Asset-scoped users only see authorized assets.
Admins can access all assets.
Remediation creator cannot approve the same job.
created_by and approved_by are derived from the authenticated user.
Audit logs record sensitive actions.
Tests pass.
Alembic is current.
The backend starts successfully with uvicorn.
```

