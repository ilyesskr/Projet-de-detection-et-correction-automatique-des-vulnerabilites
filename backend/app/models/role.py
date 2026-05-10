"""Role ORM model and the user_roles M2M association.

The set of permissions a role grants is *not* stored in the database — see
``app/core/permissions.py``. The ``roles`` table only holds the named roles
themselves so that ``user_roles`` can FK to a real row.
"""

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# (user_id, role_id) — composite primary key. Plain ``Table`` rather than an
# ORM class because the association carries no extra columns and we never
# need to query it directly.
user_role_table = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        String(36),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Role(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "roles"

    # Stable identifier referenced from code (``Role.ADMIN.value`` etc.).
    # The unique constraint at the DB level mirrors the enum invariant.
    name: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False,
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return f"<Role id={self.id} name={self.name!r}>"
