"""User management service.

Handles user CRUD plus asset-scope grants. Each function writes one audit
row but does not commit — the route owns the transaction so the audit row
and the business change land together.

Errors raise :class:`UserError` with a message the route layer maps to an
HTTP status (404 / 409 / 400 / 403) by inspecting the message, mirroring
``RemediationError`` in ``remediation_service``.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Asset, Role, User, user_asset_scope_table
from app.services.audit_service import record_audit


class UserError(Exception):
    """Raised for any user-management failure that the route layer should
    translate into a 4xx response."""


# ============================================================================
# Helpers
# ============================================================================

def _resolve_roles(db: Session, role_names: list[str]) -> list[Role]:
    """Return the Role rows for every name; raise UserError on any miss.

    Refusing to silently skip unknown names — a typo in the request must
    surface as an explicit error rather than a partially-applied update.
    """
    if not role_names:
        return []
    found = db.execute(
        select(Role).where(Role.name.in_(role_names))
    ).scalars().all()
    found_names = {r.name for r in found}
    missing = [n for n in role_names if n not in found_names]
    if missing:
        raise UserError(f"Unknown role name(s): {missing}")
    return list(found)


# ============================================================================
# Create
# ============================================================================

def create_user(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
    is_active: bool,
    is_superuser: bool,
    role_names: list[str],
    actor: str,
) -> User:
    """Create a new user. Username and email must be unique."""
    if db.execute(select(User).where(User.username == username)).scalar_one_or_none():
        raise UserError(f"Username already in use: {username!r}")
    if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
        raise UserError(f"Email already in use: {email!r}")

    roles = _resolve_roles(db, role_names)
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        is_active=is_active,
        is_superuser=is_superuser,
    )
    user.roles = roles
    db.add(user)
    db.flush()  # populate user.id for the audit row

    record_audit(
        db,
        actor=actor,
        action="user.created",
        entity_type="user",
        entity_id=user.id,
        success=True,
        context={
            "username":     username,
            "email":        email,
            "is_superuser": is_superuser,
            "role_names":   sorted(r.name for r in roles),
        },
    )
    return user


# ============================================================================
# Update
# ============================================================================

def update_user(
    db: Session,
    *,
    user_id: str,
    actor: str,
    email: str | None = None,
    password: str | None = None,
    is_active: bool | None = None,
    is_superuser: bool | None = None,
    role_names: list[str] | None = None,
) -> User:
    """Apply the partial update. Fields not provided are left untouched."""
    user = db.get(User, user_id)
    if user is None:
        raise UserError(f"User {user_id!r} not found.")

    changes: dict[str, object] = {}

    if email is not None and email != user.email:
        clash = db.execute(
            select(User).where(User.email == email, User.id != user.id)
        ).scalar_one_or_none()
        if clash is not None:
            raise UserError(f"Email already in use: {email!r}")
        user.email = email
        changes["email"] = email

    if password is not None:
        user.hashed_password = hash_password(password)
        changes["password"] = "changed"

    if is_active is not None and is_active != user.is_active:
        user.is_active = is_active
        changes["is_active"] = is_active

    if is_superuser is not None and is_superuser != user.is_superuser:
        user.is_superuser = is_superuser
        changes["is_superuser"] = is_superuser

    if role_names is not None:
        new_roles = _resolve_roles(db, role_names)
        user.roles = new_roles
        changes["role_names"] = sorted(r.name for r in new_roles)

    record_audit(
        db,
        actor=actor,
        action="user.updated",
        entity_type="user",
        entity_id=user.id,
        success=True,
        context=changes or {"note": "no-op patch"},
    )
    return user


# ============================================================================
# Delete
# ============================================================================

def delete_user(db: Session, *, user_id: str, actor: str, actor_user_id: str) -> None:
    """Hard-delete a user. Refuses if the actor is the same user (no
    self-foot-shooting). Cascades remove ``user_roles`` and
    ``user_asset_scopes``; audit rows survive (actor is a free string)."""
    user = db.get(User, user_id)
    if user is None:
        raise UserError(f"User {user_id!r} not found.")
    if user.id == actor_user_id:
        raise UserError("Cannot delete the account you are logged in as.")

    record_audit(
        db,
        actor=actor,
        action="user.deleted",
        entity_type="user",
        entity_id=user.id,
        success=True,
        context={"username": user.username, "email": user.email},
    )
    db.delete(user)


# ============================================================================
# Asset scope
# ============================================================================

def grant_asset_scope(
    db: Session,
    *,
    user_id: str,
    asset_id: str,
    actor: str,
) -> None:
    """Add a (user_id, asset_id) row to ``user_asset_scopes``. Idempotent."""
    user = db.get(User, user_id)
    if user is None:
        raise UserError(f"User {user_id!r} not found.")
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise UserError(f"Asset {asset_id!r} not found.")

    existing = db.execute(
        select(user_asset_scope_table.c.user_id).where(
            user_asset_scope_table.c.user_id == user_id,
            user_asset_scope_table.c.asset_id == asset_id,
        )
    ).first()
    if existing is not None:
        # Idempotent — record the no-op in audit so re-grants are visible
        # but do not error.
        record_audit(
            db, actor=actor,
            action="user.scope.granted",
            entity_type="user", entity_id=user_id,
            success=True,
            context={"asset_id": asset_id, "note": "already granted"},
        )
        return

    db.execute(
        user_asset_scope_table.insert().values(user_id=user_id, asset_id=asset_id)
    )
    record_audit(
        db, actor=actor,
        action="user.scope.granted",
        entity_type="user", entity_id=user_id,
        success=True,
        context={"asset_id": asset_id},
    )


def revoke_asset_scope(
    db: Session,
    *,
    user_id: str,
    asset_id: str,
    actor: str,
) -> None:
    """Remove a (user_id, asset_id) row. Idempotent."""
    if db.get(User, user_id) is None:
        raise UserError(f"User {user_id!r} not found.")

    db.execute(
        user_asset_scope_table.delete().where(
            user_asset_scope_table.c.user_id == user_id,
            user_asset_scope_table.c.asset_id == asset_id,
        )
    )
    record_audit(
        db, actor=actor,
        action="user.scope.revoked",
        entity_type="user", entity_id=user_id,
        success=True,
        context={"asset_id": asset_id},
    )


def list_asset_scope(db: Session, *, user_id: str) -> list[Asset]:
    """Return every Asset the given user is explicitly scoped to.

    Note: the user's actual visibility is `is_superuser OR these assets`. A
    superuser with zero rows here still sees everything.
    """
    if db.get(User, user_id) is None:
        raise UserError(f"User {user_id!r} not found.")
    stmt = (
        select(Asset)
        .join(
            user_asset_scope_table,
            user_asset_scope_table.c.asset_id == Asset.id,
        )
        .where(user_asset_scope_table.c.user_id == user_id)
        .order_by(Asset.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())
