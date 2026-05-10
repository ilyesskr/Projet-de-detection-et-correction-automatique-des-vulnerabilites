"""Remediation job lifecycle endpoints.

State transitions are all explicit POST routes. The frontend cannot mutate a
job by PATCHing the resource directly — every state change goes through a
dedicated endpoint that runs the corresponding service function and writes an
audit row.

``created_by`` and ``approved_by`` are derived from the authenticated user
(JWT) rather than accepted in request bodies, so the frontend cannot
spoof who created or approved a job.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    apply_asset_scope,
    get_ansible,
    get_wazuh,
    require_asset_access,
    require_permission,
)
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import RemediationJob, User
from app.schemas.common import Page
from app.schemas.remediation import (
    RemediationJobApprove,
    RemediationJobCreate,
    RemediationJobRead,
    RemediationStatus,
)
from app.services.ansible_client import AnsibleClient, AnsibleError
from app.services.remediation_service import (
    RemediationError,
    approve_job,
    create_job,
    launch_job,
    refresh_job,
    verify_job,
)
from app.services.wazuh_client import WazuhClient, WazuhError

router = APIRouter(prefix="/remediation/jobs", tags=["remediation"])


def _http_for_remediation(exc: RemediationError) -> HTTPException:
    """Map service errors to HTTP status codes by inspecting the message.

    Crude string matching, but all error sources are inside our codebase so
    the contract is stable. If the surface grows, we'll swap to typed
    exception subclasses.
    """
    msg = str(exc).lower()
    if "not found" in msg:
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if "expected" in msg and "status" in msg:
        # e.g. "Job X is in status 'running'; expected 'approved'..."
        return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    if "cannot approve" in msg:
        # Separation of Duties violation — creator approving own job.
        return HTTPException(status.HTTP_403_FORBIDDEN, str(exc))
    return HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


# ----- create / list / get --------------------------------------------------

@router.post("", response_model=RemediationJobRead, status_code=status.HTTP_201_CREATED)
def create(
    body: RemediationJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_CREATE)),
) -> RemediationJobRead:
    # Asset scope is enforced here even before the service runs — a user
    # without scope on the target asset cannot create a job for it.
    require_asset_access(body.asset_id, current_user, db)
    try:
        job = create_job(
            db,
            asset_id=body.asset_id,
            vulnerability_id=body.vulnerability_id,
            action=body.action,
            created_by=current_user.username,
            note=body.note,
        )
    except RemediationError as exc:
        raise _http_for_remediation(exc)
    return RemediationJobRead.model_validate(job)


@router.get("", response_model=Page[RemediationJobRead])
def list_jobs(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    job_status: RemediationStatus | None = Query(
        None, alias="status",
        description="Filter by lifecycle status.",
    ),
    asset_id: str | None = Query(None),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_READ)),
) -> Page[RemediationJobRead]:
    stmt = select(RemediationJob)
    if job_status:
        stmt = stmt.where(RemediationJob.status == job_status)
    if asset_id:
        stmt = stmt.where(RemediationJob.asset_id == asset_id)
    stmt = apply_asset_scope(stmt, current_user, RemediationJob.asset_id)

    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar() or 0
    items = db.execute(
        stmt.order_by(RemediationJob.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all()

    return Page[RemediationJobRead](
        items=items, total=total, limit=limit, offset=offset,
    )


@router.get("/{job_id}", response_model=RemediationJobRead)
def get_job_detail(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_READ)),
) -> RemediationJobRead:
    job = db.get(RemediationJob, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    require_asset_access(job.asset_id, current_user, db)
    return RemediationJobRead.model_validate(job)


# ----- state transitions ----------------------------------------------------

@router.post("/{job_id}/approve", response_model=RemediationJobRead)
def approve(
    job_id: str,
    body: RemediationJobApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_APPROVE)),
) -> RemediationJobRead:
    # Pre-fetch to enforce asset scope before the service mutates state.
    job = db.get(RemediationJob, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    require_asset_access(job.asset_id, current_user, db)
    try:
        job = approve_job(
            db,
            job_id=job_id,
            approved_by=current_user.username,
            note=body.note,
        )
    except RemediationError as exc:
        raise _http_for_remediation(exc)
    return RemediationJobRead.model_validate(job)


@router.post("/{job_id}/launch", response_model=RemediationJobRead)
async def launch(
    job_id: str,
    db: Session = Depends(get_db),
    awx: AnsibleClient = Depends(get_ansible),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_LAUNCH)),
) -> RemediationJobRead:
    job = db.get(RemediationJob, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    require_asset_access(job.asset_id, current_user, db)
    try:
        job = await launch_job(db, awx, job_id=job_id, actor=current_user.username)
    except RemediationError as exc:
        raise _http_for_remediation(exc)
    except AnsibleError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"awx: {exc}")
    return RemediationJobRead.model_validate(job)


@router.post("/{job_id}/refresh", response_model=RemediationJobRead)
async def refresh(
    job_id: str,
    db: Session = Depends(get_db),
    awx: AnsibleClient = Depends(get_ansible),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_LAUNCH)),
) -> RemediationJobRead:
    job = db.get(RemediationJob, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    require_asset_access(job.asset_id, current_user, db)
    try:
        job = await refresh_job(db, awx, job_id=job_id, actor=current_user.username)
    except RemediationError as exc:
        raise _http_for_remediation(exc)
    except AnsibleError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"awx: {exc}")
    return RemediationJobRead.model_validate(job)


@router.post("/{job_id}/verify", response_model=RemediationJobRead)
async def verify(
    job_id: str,
    db: Session = Depends(get_db),
    wazuh: WazuhClient = Depends(get_wazuh),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_VERIFY)),
) -> RemediationJobRead:
    job = db.get(RemediationJob, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    require_asset_access(job.asset_id, current_user, db)
    try:
        job = await verify_job(db, wazuh, job_id=job_id, actor=current_user.username)
    except RemediationError as exc:
        raise _http_for_remediation(exc)
    except WazuhError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"wazuh: {exc}")
    return RemediationJobRead.model_validate(job)
