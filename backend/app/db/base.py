"""SQLAlchemy declarative base and shared column mixins.

All ORM models inherit from ``Base`` and combine the mixins to get a UUID
primary key and ``created_at`` / ``updated_at`` timestamps for free.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Project-wide declarative base.

    All models inherit from this. Alembic discovers tables through
    ``Base.metadata``.
    """


class UUIDPrimaryKeyMixin:
    """Adds a 36-char UUID4 primary key generated Python-side.

    Stored as ``String(36)`` rather than the native PostgreSQL ``UUID`` type
    so the same ORM works unchanged against SQLite during tests.
    """

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )


class TimestampMixin:
    """Adds ``created_at`` (set once) and ``updated_at`` (auto-bumped) columns.

    ``onupdate=func.now()`` makes SQLAlchemy emit the timestamp on every
    ORM-issued UPDATE. Raw SQL touching these tables outside the ORM would
    bypass it; we will revisit with database triggers if that ever becomes a
    real path.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
