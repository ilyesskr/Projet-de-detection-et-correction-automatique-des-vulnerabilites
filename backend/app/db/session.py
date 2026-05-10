"""SQLAlchemy engine, session factory, and FastAPI dependency.

One engine per process; one session per request. Routes consume sessions via
``Depends(get_db)`` so the lifecycle (open / yield / close) is handled by the
framework.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()

# ``pool_pre_ping`` validates each connection before handing it out so we
# survive PostgreSQL idle timeouts, container restarts, and brief network
# blips. ``pool_recycle`` is belt-and-suspenders for the same class of bug.
engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    future=True,
)

# ``expire_on_commit=False`` lets routes return ORM objects after a commit
# without triggering a second SELECT to refresh attributes — important because
# FastAPI serializes the object *after* the dependency closes the session.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a session, guarantees it gets closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
