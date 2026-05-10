"""User management routes (admin-only).

All endpoints under ``/users`` require the ``users:manage`` permission and
are intended for the admin role. ``/roles`` is read-only and visible to
admins so the frontend can populate role pickers.

Routes write audit rows via ``user_service``; the actor on each row is the
authenticated admin's username, so an audit trail of who changed what is
preserved even after a user is deleted.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import Role, User
from app.schemas.asset import AssetRead
from app.schemas.common import Page
from app.schemas.user import (
    AssetScopeAssign,
    RoleRead,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.services.user_service import (
    UserError,
    create_user,
    delete_user,
    grant_asset_scope,
    list_asset_scope,
    revoke_asset_scope,
    update_user,
)

router = APIRouter(tags=["users"])


def _http_for_user(exc: UserError) -> HTTPException:
    """Translate UserError to a status code by message inspection.

    Uses the same shape as ``_http_for_remediation`` so the contract feels
    consistent across services.
    """
    msg = str(exc).lower()
    if "not found" in msg:
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if "already in use" in msg:
        return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    if "logged in as" in msg:
        return HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


# ============================================================================
# /roles — read-only catalog (no users:manage required, anyone with users:manage)
# ============================================================================

@router.get(
    "/roles",
    response_model=list[RoleRead],
    dependencies=[Depends(require_permission(Permission.USERS_MANAGE))],
)
def list_roles(db: Session = Depends(get_db)) -> list[RoleRead]:
    """List every role currently in the database, alphabetical by name."""
    rows = db.execute(select(Role).order_by(Role.name)).scalars().all()
    return [RoleRead.model_validate(r) for r in rows]


# ============================================================================
# /users — CRUD
# ============================================================================

@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def create(
    body: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USERS_MANAGE)),
) -> UserRead:
    try:
        user = create_user(
            db,
            username=body.username,
            email=str(body.email),
            password=body.password,
            is_active=body.is_active,
            is_superuser=body.is_superuser,
            role_names=body.role_names,
            actor=current_user.username,
        )
    except UserError as exc:
        raise _http_for_user(exc)
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.get("/users", response_model=Page[UserRead])
def list_users(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    is_active: bool | None = Query(None),
    _admin: User = Depends(require_permission(Permission.USERS_MANAGE)),
) -> Page[UserRead]:
    """Paginated user list, newest first. Optional active-only filter."""
    stmt = select(User)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
    items = db.execute(
        stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all()
    return Page[UserRead](items=items, total=total, limit=limit, offset=offset)


@router.get("/users/{user_id}", response_model=UserRead)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_permission(Permission.USERS_MANAGE)),
) -> UserRead:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    return UserRead.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserRead)
def patch_user(
    user_id: str,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USERS_MANAGE)),
) -> UserRead:
    try:
        user = update_user(
            db,
            user_id=user_id,
            actor=current_user.username,
            email=str(body.email) if body.email is not None else None,
            password=body.password,
            is_active=body.is_active,
            is_superuser=body.is_superuser,
            role_names=body.role_names,
        )
    except UserError as exc:
        raise _http_for_user(exc)
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USERS_MANAGE)),
) -> None:
    try:
        delete_user(
            db,
            user_id=user_id,
            actor=current_user.username,
            actor_user_id=current_user.id,
        )
    except UserError as exc:
        raise _http_for_user(exc)
    db.commit()


# ============================================================================
# Asset scope management
# ============================================================================

@router.get(
    "/users/{user_id}/asset-scopes",
    response_model=list[AssetRead],
)
def get_user_asset_scope(
    user_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_permission(Permission.USERS_MANAGE)),
) -> list[AssetRead]:
    """List the assets a user is explicitly scoped to.

    Empty list does NOT mean "no access" for superusers — they bypass scope
    entirely. Check ``is_superuser`` on the user to interpret correctly.
    """
    try:
        assets = list_asset_scope(db, user_id=user_id)
    except UserError as exc:
        raise _http_for_user(exc)
    return [AssetRead.model_validate(a) for a in assets]


@router.post(
    "/users/{user_id}/asset-scopes",
    status_code=status.HTTP_204_NO_CONTENT,
)
def add_user_asset_scope(
    user_id: str,
    body: AssetScopeAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USERS_MANAGE)),
) -> None:
    try:
        grant_asset_scope(
            db,
            user_id=user_id,
            asset_id=body.asset_id,
            actor=current_user.username,
        )
    except UserError as exc:
        raise _http_for_user(exc)
    db.commit()


@router.delete(
    "/users/{user_id}/asset-scopes/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_user_asset_scope(
    user_id: str,
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USERS_MANAGE)),
) -> None:
    try:
        revoke_asset_scope(
            db,
            user_id=user_id,
            asset_id=asset_id,
            actor=current_user.username,
        )
    except UserError as exc:
        raise _http_for_user(exc)
    db.commit()
