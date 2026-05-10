"""Wazuh sync triggers.

Both routes are POST (they mutate state) and synchronous from the caller's
POV — they wait for the sync to finish and return a summary. For very large
fleets this can take a while; if that becomes a UX problem we move to a
background-job model and have the route return a job id immediately.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_wazuh, require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import User
from app.services.sync_service import SyncResult, sync_agents, sync_vulnerabilities
from app.services.wazuh_client import WazuhClient, WazuhError

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/wazuh/agents", response_model=SyncResult)
async def sync_agents_route(
    db: Session = Depends(get_db),
    wazuh: WazuhClient = Depends(get_wazuh),
    current_user: User = Depends(require_permission(Permission.SYNC_RUN)),
) -> SyncResult:
    """Pull all Wazuh agents and upsert into ``assets``."""
    try:
        return await sync_agents(db, wazuh, actor=current_user.username)
    except WazuhError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"wazuh: {exc}",
        )


@router.post("/wazuh/vulnerabilities", response_model=SyncResult)
async def sync_vulnerabilities_route(
    db: Session = Depends(get_db),
    wazuh: WazuhClient = Depends(get_wazuh),
    current_user: User = Depends(require_permission(Permission.SYNC_RUN)),
) -> SyncResult:
    """Pull every asset's CVE list and reconcile with the local DB."""
    # Note: per-asset Wazuh failures don't raise; they're surfaced inside the
    # ``errors`` list of the SyncResult. Whole-run failures (e.g. Wazuh down)
    # raise WazuhError from sync_agents-style fetch and we map to 502.
    try:
        return await sync_vulnerabilities(db, wazuh, actor=current_user.username)
    except WazuhError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"wazuh: {exc}",
        )
