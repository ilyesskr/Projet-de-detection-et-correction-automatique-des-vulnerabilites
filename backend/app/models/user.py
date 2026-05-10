"""User ORM model and the user_asset_scopes M2M association.

A user belongs to zero or more roles (``user_roles``) and has zero or more
asset scopes (``user_asset_scopes``). When a user has *no* asset scopes, the
default rule is "no asset access" — the only escape hatch is
``is_superuser=True``, which bypasses scope filtering entirely.
"""

from sqlalchemy import Boolean, Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.role import Role, user_role_table

# (user_id, asset_id) — restricts a user to a specific subset of assets.
# Admins typically have NO rows here and rely on ``is_superuser=True`` to
# bypass the filter; analysts/operators have explicit rows per asset.
user_asset_scope_table = Table(
    "user_asset_scopes",
    Base.metadata,
    Column(
        "user_id",
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "asset_id",
        String(36),
        ForeignKey("assets.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    # Identity. Both unique and indexed so login-by-username and
    # login-by-email work the same.
    username: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False,
    )

    # bcrypt hash of the password. Plaintext never lives here.
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Inactive users cannot log in. Used to deactivate accounts without
    # losing audit history.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Independent of role membership. ``is_superuser=True`` is the *only*
    # mechanism that bypasses asset-scope filtering — even the ``admin`` role
    # respects scopes unless this flag is set.
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # M2M relationships. ``lazy="selectin"`` so accessing ``user.roles``
    # inside ``get_current_user`` doesn't trigger an N+1.
    roles: Mapped[list[Role]] = relationship(
        secondary=user_role_table,
        lazy="selectin",
    )
    # Plain ``list[str]`` would lose the asset relationship; using ``Asset``
    # would create a circular import. We expose the IDs through a separate
    # query when scope filtering needs them.

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return f"<User id={self.id} username={self.username!r}>"
