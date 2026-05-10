"""Audit log listing — read-only, paginated, filterable."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import AuditLog
from app.schemas.audit import AuditLogRead
from app.schemas.common import Page

router = APIRouter(
    prefix="/audit-logs",
    tags=["audit"],
    dependencies=[Depends(require_permission(Permission.AUDIT_READ))],
)


@router.get("", response_model=Page[AuditLogRead])
def list_audit_logs(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: str | None = Query(None, description="Exact action name match."),
    actor: str | None = Query(None),
    entity_id: str | None = Query(None),
) -> Page[AuditLogRead]:
    """Newest-first audit history. Filters AND together."""
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if actor:
        stmt = stmt.where(AuditLog.actor == actor)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)

    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar() or 0
    items = db.execute(
        stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all()

    return Page[AuditLogRead](
        items=items, total=total, limit=limit, offset=offset,
    )
