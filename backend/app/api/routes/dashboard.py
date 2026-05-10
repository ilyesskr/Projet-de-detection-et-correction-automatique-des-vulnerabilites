"""Dashboard summary — one round-trip the frontend home page can render from.

Aggregates the counts and integration-reachability flags the operator dashboard
needs without forcing the frontend to fan out to four list endpoints and two
health endpoints. Every count respects the caller's asset scope so a scoped
user sees only their slice.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    apply_asset_scope,
    get_ansible,
    get_current_user,
    get_wazuh,
)
from app.db.session import get_db
from app.models import Asset, RemediationJob, User, Vulnerability
from app.services.ansible_client import AnsibleClient, AnsibleError
from app.services.wazuh_client import WazuhClient, WazuhError

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# Buckets are listed explicitly so the frontend always gets a stable shape —
# zero-count keys still appear, which keeps the UI from having to guess at
# which severities or statuses exist.
_SEVERITY_BUCKETS = ("critical", "high", "medium", "low")
_JOB_STATUS_BUCKETS = (
    "pending_approval",
    "approved",
    "running",
    "verification_pending",
    "verified_fixed",
    "failed",
    "cancelled",
)


class DashboardSummary(BaseModel):
    assets_total: int
    assets_active: int
    vulns_open_by_severity: dict[str, int]
    jobs_by_status: dict[str, int]
    wazuh_reachable: bool
    awx_reachable: bool


async def _is_reachable_wazuh(wazuh: WazuhClient) -> bool:
    try:
        await wazuh.health()
    except WazuhError:
        return False
    return True


async def _is_reachable_awx(awx: AnsibleClient) -> bool:
    try:
        await awx.health()
    except AnsibleError:
        return False
    return True


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    db: Session = Depends(get_db),
    wazuh: WazuhClient = Depends(get_wazuh),
    awx: AnsibleClient = Depends(get_ansible),
    current_user: User = Depends(get_current_user),
) -> DashboardSummary:
    """Aggregate counts + integration reachability for the home page.

    Permission: any authenticated user. Counts are filtered to the user's
    asset scope (superusers see everything).
    """
    # ----- assets ----------------------------------------------------------
    assets_stmt = apply_asset_scope(select(Asset.id), current_user, Asset.id)
    assets_total = db.execute(
        select(func.count()).select_from(assets_stmt.subquery())
    ).scalar() or 0

    active_stmt = apply_asset_scope(
        select(Asset.id).where(Asset.status == "active"),
        current_user,
        Asset.id,
    )
    assets_active = db.execute(
        select(func.count()).select_from(active_stmt.subquery())
    ).scalar() or 0

    # ----- open vulnerabilities by severity --------------------------------
    vuln_stmt = apply_asset_scope(
        select(Vulnerability.severity, func.count(Vulnerability.id))
        .where(Vulnerability.status == "open")
        .group_by(Vulnerability.severity),
        current_user,
        Vulnerability.asset_id,
    )
    vuln_rows = db.execute(vuln_stmt).all()
    vulns_open_by_severity = {bucket: 0 for bucket in _SEVERITY_BUCKETS}
    for severity, count in vuln_rows:
        # Wazuh occasionally reports "unknown"/other vocabulary — drop it
        # rather than inventing a new bucket the frontend has no slot for.
        if severity in vulns_open_by_severity:
            vulns_open_by_severity[severity] = count

    # ----- remediation jobs by status --------------------------------------
    job_stmt = apply_asset_scope(
        select(RemediationJob.status, func.count(RemediationJob.id))
        .group_by(RemediationJob.status),
        current_user,
        RemediationJob.asset_id,
    )
    job_rows = db.execute(job_stmt).all()
    jobs_by_status = {bucket: 0 for bucket in _JOB_STATUS_BUCKETS}
    for job_status, count in job_rows:
        if job_status in jobs_by_status:
            jobs_by_status[job_status] = count

    # ----- integrations ----------------------------------------------------
    return DashboardSummary(
        assets_total=assets_total,
        assets_active=assets_active,
        vulns_open_by_severity=vulns_open_by_severity,
        jobs_by_status=jobs_by_status,
        wazuh_reachable=await _is_reachable_wazuh(wazuh),
        awx_reachable=await _is_reachable_awx(awx),
    )
