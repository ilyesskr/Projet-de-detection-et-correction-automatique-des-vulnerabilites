"""User and Role API schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class RoleRead(ORMModel):
    id: str
    name: str
    description: str | None = None


class UserCreate(BaseModel):
    """Body for ``POST /users`` (admin-only).

    The plaintext password is hashed server-side before being stored. The
    frontend never sends ``hashed_password`` directly.
    """

    username: str = Field(..., min_length=1, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    is_active: bool = True
    is_superuser: bool = False
    role_names: list[str] = Field(
        default_factory=list,
        description="Names of existing roles to grant the new user.",
    )


class UserUpdate(BaseModel):
    """Body for ``PATCH /users/{id}``. Every field is optional — fields the
    caller omits are left unchanged.

    ``role_names``, when provided, *replaces* the user's full role set; pass
    ``[]`` to strip every role. Username is intentionally not editable —
    rename a user by deleting and recreating, so audit references stay
    interpretable.
    """

    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8, max_length=128)
    is_active: bool | None = None
    is_superuser: bool | None = None
    role_names: list[str] | None = None


class UserRead(ORMModel):
    """Public view of a user. Excludes ``hashed_password`` deliberately."""

    id: str
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    roles: list[RoleRead] = []
    created_at: datetime
    updated_at: datetime


class UserSelf(UserRead):
    """``GET /auth/me`` adds the resolved permission set so the frontend can
    enable/disable buttons without consulting the role→permission mapping
    itself.
    """

    permissions: list[str] = []


class AssetScopeAssign(BaseModel):
    """Body for ``POST /users/{id}/asset-scopes`` — grant access to one asset."""

    asset_id: str
