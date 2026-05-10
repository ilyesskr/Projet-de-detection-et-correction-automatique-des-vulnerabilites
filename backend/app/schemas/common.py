"""Shared Pydantic primitives used by every entity schema.

- ``ORMModel``: base for every "Read" schema. Sets ``from_attributes=True`` so
  schemas can be built directly from SQLAlchemy ORM objects, without having to
  call ``.model_validate(orm_obj.__dict__)`` at each callsite.
- ``Page[T]``: standard envelope for every paginated list endpoint. Frontends
  only need to learn this one shape.
- ``HealthResponse``: tiny shared shape used by /health and /api/v1/health.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Base for response schemas built from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Standard paginated list envelope: ``{items, total, limit, offset}``."""

    items: list[T]
    total: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    """Minimal shape returned by health endpoints."""

    status: str
    detail: str | None = None
