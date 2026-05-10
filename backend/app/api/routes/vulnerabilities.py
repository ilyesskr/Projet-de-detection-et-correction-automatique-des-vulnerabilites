"""Vulnerability listing with the filters the frontend needs most."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import apply_asset_scope, require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import User, Vulnerability
from app.schemas.common import Page
from app.schemas.vulnerability import Severity, VulnerabilityRead, VulnStatus

router = APIRouter(prefix="/vulnerabilities", tags=["vulnerabilities"])


@router.get("", response_model=Page[VulnerabilityRead])
def list_vulnerabilities(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    asset_id: str | None = Query(None),
    severity: Severity | None = Query(None),
    status: VulnStatus | None = Query(None),
    cve: str | None = Query(None, description="Exact CVE match, e.g. CVE-2024-1234"),
    current_user: User = Depends(require_permission(Permission.VULNERABILITIES_READ)),
) -> Page[VulnerabilityRead]:
    """Paginated, filterable vulnerability list.

    Filter behavior: each filter narrows the result set (logical AND). Omit
    a filter to leave it open. ``severity`` and ``status`` are validated
    against the documented vocabularies — typos return 422, not silent empty.

    Results are also restricted to the user's asset scope (superusers
    bypass).
    """
    stmt = select(Vulnerability)
    if asset_id:
        stmt = stmt.where(Vulnerability.asset_id == asset_id)
    if severity:
        stmt = stmt.where(Vulnerability.severity == severity)
    if status:
        stmt = stmt.where(Vulnerability.status == status)
    if cve:
        stmt = stmt.where(Vulnerability.cve == cve)
    stmt = apply_asset_scope(stmt, current_user, Vulnerability.asset_id)

    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar() or 0
    items = db.execute(
        stmt.order_by(Vulnerability.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all()

    return Page[VulnerabilityRead](
        items=items, total=total, limit=limit, offset=offset,
    )
