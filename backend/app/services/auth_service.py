"""Authentication service.

Login is a two-step operation:

1. Locate the user by username *or* email — we accept either as the login
   identifier and pick whichever column matches.
2. Verify the supplied password against the stored bcrypt hash.

Inactive users are rejected at step 1 so we never leak whether the username
itself exists. The route layer wraps the result into a ``TokenResponse``.

This module deliberately does *not* commit audit rows on its own — the
caller owns the transaction so the audit log and the login outcome land
together. ``record_login_attempt`` is provided as a convenience for the
route to call.
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    verify_password,
)
from app.models import User
from app.services.audit_service import record_audit


def get_user_by_identifier(db: Session, identifier: str) -> User | None:
    """Return the active user whose username *or* email matches ``identifier``.

    Inactive accounts are filtered out here so login attempts against them
    fail with the same generic error as a wrong password — no information
    leak about whether the account exists.
    """
    stmt = select(User).where(
        or_(User.username == identifier, User.email == identifier),
        User.is_active.is_(True),
    )
    return db.execute(stmt).scalar_one_or_none()


def authenticate(db: Session, *, identifier: str, password: str) -> User | None:
    """Return the matching active user iff ``password`` is correct.

    Returns ``None`` for any failure (no user, wrong password, inactive
    account). The caller logs the failure and returns 401 — never disclose
    which condition failed.
    """
    user = get_user_by_identifier(db, identifier)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def issue_token(user: User) -> str:
    """Wrap ``create_access_token`` so callers don't import core.security."""
    return create_access_token(user_id=user.id, username=user.username)


def record_login_attempt(
    db: Session,
    *,
    identifier: str,
    user: User | None,
    success: bool,
    reason: str | None = None,
) -> None:
    """Emit an audit row for a login attempt.

    Always logs the supplied identifier (so failed attempts on unknown
    accounts are visible), and the resolved ``user.id`` when known so the
    frontend can correlate sessions to users.
    """
    record_audit(
        db,
        actor=user.username if user else identifier,
        action="auth.login.success" if success else "auth.login.failed",
        entity_type="user" if user else None,
        entity_id=user.id if user else None,
        success=success,
        context={"identifier": identifier, "reason": reason} if reason else {"identifier": identifier},
    )
