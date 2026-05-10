"""Asset listing routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    apply_asset_scope,
    require_asset_access,
    require_permission,
)
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import Asset, User, Vulnerability
from app.schemas.asset import AssetRead
from app.schemas.common import Page
from app.schemas.vulnerability import VulnerabilityRead

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=Page[AssetRead])
def list_assets(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: str | None = Query(
        None,
        description="Case-insensitive substring match on hostname.",
    ),
    current_user: User = Depends(require_permission(Permission.ASSETS_READ)),
) -> Page[AssetRead]:
    """Paginated list of assets, newest first. Optional hostname filter.

    Filtered to the user's asset scope; superusers see everything.
    """
    stmt = select(Asset)
    if search:
        stmt = stmt.where(Asset.hostname.ilike(f"%{search}%"))
    stmt = apply_asset_scope(stmt, current_user, Asset.id)

    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar() or 0
    items = db.execute(
        stmt.order_by(Asset.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all()

    return Page[AssetRead](items=items, total=total, limit=limit, offset=offset)


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ASSETS_READ)),
) -> AssetRead:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="asset not found",
        )
    require_asset_access(asset_id, current_user, db)
    return AssetRead.model_validate(asset)


@router.get(
    "/{asset_id}/vulnerabilities",
    response_model=Page[VulnerabilityRead],
)
def get_asset_vulnerabilities(
    asset_id: str,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission(Permission.VULNERABILITIES_READ)),
) -> Page[VulnerabilityRead]:
    """Vulnerabilities scoped to a single asset."""
    if db.get(Asset, asset_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="asset not found",
        )
    require_asset_access(asset_id, current_user, db)

    stmt = select(Vulnerability).where(Vulnerability.asset_id == asset_id)
    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar() or 0
    items = db.execute(
        stmt.order_by(Vulnerability.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all()

    return Page[VulnerabilityRead](
        items=items, total=total, limit=limit, offset=offset,
    )
