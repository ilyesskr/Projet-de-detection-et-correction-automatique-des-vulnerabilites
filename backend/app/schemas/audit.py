"""Audit log API schemas — read-only, surfaced by /audit-logs."""

from datetime import datetime
from typing import Any

from app.schemas.common import ORMModel


class AuditLogRead(ORMModel):
    """One row from the append-only audit log."""

    id: str
    actor: str
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    success: bool
    context: dict[str, Any] | None = None
    created_at: datetime
