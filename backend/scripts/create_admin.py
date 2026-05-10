"""Bootstrap script: seed the four named roles and the first admin user.

Run from ``backend/``::

    .venv/bin/python -m scripts.create_admin

Reads ``FIRST_ADMIN_USERNAME``, ``FIRST_ADMIN_EMAIL``, ``FIRST_ADMIN_PASSWORD``
from the environment / ``.env``. Idempotent: re-running adds nothing if the
roles and user already exist (only sets the admin role assignment if missing).

Why a script and not an Alembic data migration: roles are stable but the
admin password is environment-specific and should not appear in the
migration history. Keeping admin creation out of Alembic also lets test
fixtures construct users directly without running the bootstrap.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow ``python -m scripts.create_admin`` from either backend/ or
# backend/scripts/ — append the backend root so ``app.*`` resolves.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import select  # noqa: E402

from app.core.permissions import Role as RoleEnum  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import Role, User  # noqa: E402


# Human-readable descriptions per role. Stored on the row so the future UI
# doesn't have to invent them.
_ROLE_DESCRIPTIONS: dict[str, str] = {
    RoleEnum.ADMIN.value:                "Full platform access including user management.",
    RoleEnum.SECURITY_ANALYST.value:     "Reads assets/vulns, runs sync, creates remediation jobs.",
    RoleEnum.REMEDIATION_OPERATOR.value: "Reads assets/vulns, approves and launches remediation jobs.",
    RoleEnum.VIEWER.value:               "Read-only access to assets, vulnerabilities, and audit logs.",
}


def _ensure_roles(db) -> dict[str, Role]:
    """Create the four named roles if missing. Returns ``{name: Role}``."""
    by_name: dict[str, Role] = {}
    for name in (r.value for r in RoleEnum):
        role = db.execute(select(Role).where(Role.name == name)).scalar_one_or_none()
        if role is None:
            role = Role(name=name, description=_ROLE_DESCRIPTIONS[name])
            db.add(role)
            db.flush()
            print(f"  + role {name!r} created")
        else:
            print(f"  · role {name!r} already exists")
        by_name[name] = role
    return by_name


def _ensure_admin_user(db, roles: dict[str, Role]) -> User:
    """Create the admin user if missing; ensure it has the admin role."""
    username = os.environ.get("FIRST_ADMIN_USERNAME") or "admin"
    email    = os.environ.get("FIRST_ADMIN_EMAIL")    or "admin@example.com"
    password = os.environ.get("FIRST_ADMIN_PASSWORD")
    if not password:
        raise SystemExit(
            "FIRST_ADMIN_PASSWORD is not set. "
            "Set it in .env or the environment before running this script."
        )

    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.flush()
        print(f"  + admin user {username!r} created")
    else:
        print(f"  · admin user {username!r} already exists")

    admin_role = roles[RoleEnum.ADMIN.value]
    if admin_role not in user.roles:
        user.roles.append(admin_role)
        print(f"  + granted {RoleEnum.ADMIN.value} role to {username!r}")
    else:
        print(f"  · {username!r} already has the {RoleEnum.ADMIN.value} role")

    return user


def main() -> int:
    print("Seeding roles and bootstrap admin user...")
    db = SessionLocal()
    try:
        roles = _ensure_roles(db)
        _ensure_admin_user(db, roles)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
