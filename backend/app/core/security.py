"""Security primitives: password hashing and JWT issue/decode.

Password hashing uses bcrypt directly (no passlib indirection). JWT uses
PyJWT with HS256.

JWT payload is intentionally minimal — ``sub``, ``username``, ``exp`` and
nothing else. Roles and permissions are loaded from the database in
``get_current_user`` so a role change takes effect on the user's next
request rather than waiting for the token to expire.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings


# ============================================================================
# Errors
# ============================================================================

class TokenError(Exception):
    """Raised by ``decode_access_token`` for any invalid/expired/malformed JWT.

    Routes catch this and translate to HTTP 401 — callers should not need to
    import ``jwt`` to handle errors.
    """


# ============================================================================
# Password hashing
# ============================================================================

def hash_password(password: str) -> str:
    """Return a bcrypt hash of ``password`` as a UTF-8 string.

    Bcrypt's default cost factor (12) is appropriate for an internal tool;
    raise it later if the user count grows enough to justify the latency.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True iff ``plain_password`` matches the stored ``hashed_password``.

    Returns False on any decoding error so a corrupted hash never raises into
    the auth path — login simply fails.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


# ============================================================================
# JWT issue / decode
# ============================================================================

def create_access_token(*, user_id: str, username: str) -> str:
    """Issue a signed JWT for ``user_id``.

    The payload deliberately carries only identity claims. Roles and
    permissions are resolved from the database on each request — see
    ``get_current_user`` in ``app/api/dependencies.py``.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {
        "sub":      user_id,
        "username": username,
        "iat":      int(now.timestamp()),
        "exp":      int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify ``token`` and return the decoded claims.

    Raises ``TokenError`` for any invalid / expired / malformed token. The
    underlying ``jwt`` exception type is captured so callers do not need to
    depend on the PyJWT exception hierarchy.
    """
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError(f"invalid token: {exc}") from exc
