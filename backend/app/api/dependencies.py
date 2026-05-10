"""FastAPI dependencies.

Two groups live here:

1. **External API clients** — ``get_wazuh`` and ``get_ansible`` yield an
   httpx-backed client for the duration of a request and close its pool on
   exit, so we never leak connections.
2. **Auth / RBAC** — ``get_current_user`` resolves the JWT to a ``User``,
   ``require_permission`` and ``require_any_permission`` gate routes by
   permission, ``require_asset_access`` enforces single-asset scope, and
   ``apply_asset_scope`` filters list queries by scope.

The auth helpers always read the latest user state from the database; the
JWT carries identity only, so role/permission/scope changes take effect on
the user's next request rather than waiting for token expiry.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Sequence
from typing import Any, Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.permissions import Permission, permissions_for_roles
from app.core.security import TokenError, decode_access_token
from app.db.session import get_db
from app.models import User, user_asset_scope_table
from app.services.ansible_client import AnsibleClient, get_ansible_client
from app.services.wazuh_client import WazuhClient, get_wazuh_client


# ============================================================================
# External API clients
# ============================================================================

async def get_wazuh() -> AsyncGenerator[WazuhClient, None]:
    """Yield a WazuhClient for one request; close it on exit."""
    client = get_wazuh_client()
    try:
        yield client
    finally:
        await client.aclose()


async def get_ansible() -> AsyncGenerator[AnsibleClient, None]:
    """Yield an AnsibleClient for one request; close it on exit."""
    client = get_ansible_client()
    try:
        yield client
    finally:
        await client.aclose()


# ============================================================================
# Auth: resolve the JWT to a User
# ============================================================================

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated.",
    headers={"WWW-Authenticate": "Bearer"},
)


def _extract_bearer_token(request: Request) -> str:
    """Pull the bearer token out of ``Authorization`` or 401."""
    auth = request.headers.get("authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise _UNAUTHENTICATED
    return token


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Decode the JWT and load the matching active user.

    Any failure path returns 401 with the same generic detail so callers
    cannot distinguish "no token" from "expired token" from "user removed".
    """
    token = _extract_bearer_token(request)
    try:
        payload = decode_access_token(token)
    except TokenError:
        raise _UNAUTHENTICATED

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise _UNAUTHENTICATED

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _UNAUTHENTICATED
    return user


def current_user_permissions(user: User) -> frozenset[Permission]:
    """Resolve the user's roles to a permission set.

    Pulled out as a helper so audit/me/route handlers can ask the same
    question without re-implementing the role lookup.
    """
    return permissions_for_roles([r.name for r in user.roles])


# ============================================================================
# Auth: permission gates
# ============================================================================

def require_permission(permission: Permission) -> Callable[..., User]:
    """Dependency factory: route requires the named permission.

    Usage::

        @router.get("/assets")
        def list_assets(user = Depends(require_permission(Permission.ASSETS_READ))):
            ...
    """

    def _dep(current_user: User = Depends(get_current_user)) -> User:
        if permission not in current_user_permissions(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )
        return current_user

    return _dep


def require_any_permission(
    permissions: Sequence[Permission],
) -> Callable[..., User]:
    """Dependency factory: route requires *any* of the named permissions.

    Useful for read endpoints reachable from multiple roles, e.g.
    ``GET /remediation/jobs`` is fine for analyst, operator, or approver.
    """
    if not permissions:
        raise ValueError("require_any_permission needs at least one permission")

    def _dep(current_user: User = Depends(get_current_user)) -> User:
        user_perms = current_user_permissions(current_user)
        if not any(p in user_perms for p in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Missing any of required permissions: "
                    f"{[str(p) for p in permissions]}"
                ),
            )
        return current_user

    return _dep


# ============================================================================
# Auth: asset-scope filters
# ============================================================================

def user_can_access_asset(db: Session, user: User, asset_id: str) -> bool:
    """True iff ``user`` is allowed to see ``asset_id``.

    Superusers bypass scope entirely. For everyone else, an explicit row in
    ``user_asset_scopes`` is required. A user with *zero* scope rows can see
    nothing — the safe default.
    """
    if user.is_superuser:
        return True
    stmt = select(user_asset_scope_table.c.asset_id).where(
        user_asset_scope_table.c.user_id == user.id,
        user_asset_scope_table.c.asset_id == asset_id,
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def require_asset_access(
    asset_id: str,
    user: User,
    db: Session,
) -> None:
    """Raise 403 if ``user`` cannot access ``asset_id``.

    Not a dependency factory — called inline by route handlers that already
    have the user and the asset id from path params. Single-asset routes
    use this; list routes use ``apply_asset_scope`` instead.
    """
    if not user_can_access_asset(db, user, asset_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Asset is outside your access scope.",
        )


def apply_asset_scope(
    stmt: Select[Any],
    user: User,
    asset_id_column: Any,
) -> Select[Any]:
    """Restrict a list query to assets the user can see.

    For superusers, returns the statement unchanged. For everyone else, adds
    a ``WHERE asset_id IN (user's scope)`` filter using a subquery.

    ``asset_id_column`` is the column to filter on — for ``Vulnerability``
    and ``RemediationJob`` it's the FK to ``assets``; for ``Asset`` itself
    it's ``Asset.id``.
    """
    if user.is_superuser:
        return stmt
    scope = select(user_asset_scope_table.c.asset_id).where(
        user_asset_scope_table.c.user_id == user.id,
    )
    return stmt.where(asset_id_column.in_(scope))
