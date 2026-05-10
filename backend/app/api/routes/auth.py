"""Authentication routes.

``/auth/login`` is the only platform endpoint that does *not* require auth —
it's the entry point. Everything else, including ``/auth/me``, requires a
valid bearer token.

Login emits an audit row whether it succeeds or fails so failed-login
analytics are available without extra plumbing.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import current_user_permissions, get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import RoleRead, UserSelf
from app.services.auth_service import (
    authenticate,
    issue_token,
    record_login_attempt,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Exchange username/email + password for a JWT.

    Returns a generic 401 for any failure path (no such user, wrong password,
    inactive account) so the response cannot be used to enumerate accounts.
    """
    user = authenticate(db, identifier=body.username, password=body.password)
    if user is None:
        record_login_attempt(
            db,
            identifier=body.username,
            user=None,
            success=False,
            reason="invalid credentials or inactive account",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    token = issue_token(user)
    record_login_attempt(db, identifier=body.username, user=user, success=True)
    db.commit()

    settings = get_settings()
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.get("/me", response_model=UserSelf)
def me(current_user: User = Depends(get_current_user)) -> UserSelf:
    """Identity + resolved permissions for the authenticated user.

    Frontends call this once after login to learn which UI elements to
    enable, instead of re-implementing the role→permission table client-side.
    """
    return UserSelf(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        roles=[
            RoleRead(id=r.id, name=r.name, description=r.description)
            for r in current_user.roles
        ],
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        permissions=sorted(p.value for p in current_user_permissions(current_user)),
    )
