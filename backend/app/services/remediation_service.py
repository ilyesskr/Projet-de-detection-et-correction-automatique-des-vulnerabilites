r"""Remediation job lifecycle.

State machine::

    pending_approval -> approved -> running -> verification_pending -> verified_fixed
                                           \-> failed / cancelled

Each transition is its own function. Functions enforce the *expected* current
state and raise :class:`RemediationError` on bad transitions, so the frontend
can never put a job into an impossible state by retrying or racing.

Inline at the top of this file is the small **policy layer** — the mapping
from a semantic ``action`` (``package_update``, etc.) to the AWX job template
that knows how to apply it. The client never picks template IDs directly;
that would bypass policy and is a security smell.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Asset, RemediationJob, Vulnerability
from app.services.ansible_client import AnsibleClient, AnsibleError, extract_job_id
from app.services.audit_service import record_audit
from app.services.normalizers import normalize_vulnerability
from app.services.wazuh_client import WazuhClient, WazuhError


# ============================================================================
# Policy layer
# ============================================================================

# The set of supported semantic actions. Mirrors the ``RemediationAction``
# Literal at the API edge so error messages can list valid actions without
# a separate source of truth.
_KNOWN_ACTIONS: tuple[str, ...] = (
    "package_update",
    "windows_update",
    "service_restart",
    "config_change",
)


def _template_id_for(action: str) -> int | None:
    """Return the AWX template id for ``action``, or ``None`` if unconfigured.

    The mapping comes from environment-driven Settings (``AWX_TEMPLATE_*``)
    rather than a hardcoded dict, so each environment can point at its own
    approved templates without code changes.
    """
    settings = get_settings()
    return getattr(settings, f"awx_template_{action}", None)


# Translates AWX's job statuses into our platform vocabulary. AWX's terminal
# "successful" goes to ``verification_pending`` — Wazuh, not AWX, has the
# final word on whether the CVE is actually gone.
_AWX_TO_PLATFORM_STATUS: dict[str, str] = {
    "new":        "running",
    "pending":    "running",
    "waiting":    "running",
    "running":    "running",
    "successful": "verification_pending",
    "failed":     "failed",
    "error":      "failed",
    "canceled":   "cancelled",
}


# ============================================================================
# Errors
# ============================================================================

class RemediationError(Exception):
    """Raised when a remediation job operation cannot proceed.

    Caught by the route layer and translated to an HTTP error.
    """


# ============================================================================
# Internal helpers
# ============================================================================

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _build_extra_vars(
    job: RemediationJob,
    asset: Asset,
    vulnerability: Vulnerability | None,
) -> dict[str, Any]:
    """Build the playbook context AWX will receive as ``extra_vars``.

    Conventions:
    - ``pa_*`` keys are platform metadata (job/vuln/asset IDs) — playbooks log
      them so AWX runs can be correlated back to platform records.
    - The remaining keys are operational and are what playbooks actually use
      to decide what to do (which host, which package, which version).
    """
    payload: dict[str, Any] = {
        "pa_job_id": job.id,
        "pa_action": job.action,
        "asset_hostname":    asset.hostname,
        "asset_ip_address":  asset.ip_address,
        "asset_os_platform": asset.os_platform,
        "remediation_action": job.action,
    }
    if vulnerability is not None:
        payload.update({
            "pa_vulnerability_id": vulnerability.id,
            "cve":               vulnerability.cve,
            "package_name":      vulnerability.package_name,
            "installed_version": vulnerability.installed_version,
            "fixed_version":     vulnerability.fixed_version,
        })
    return payload


def _get_or_404(db: Session, job_id: str) -> RemediationJob:
    job = db.get(RemediationJob, job_id)
    if job is None:
        raise RemediationError(f"Remediation job {job_id!r} not found.")
    return job


def _expect_status(job: RemediationJob, expected: str) -> None:
    if job.status != expected:
        raise RemediationError(
            f"Job {job.id} is in status {job.status!r}; "
            f"expected {expected!r} for this transition."
        )


# ============================================================================
# Lifecycle: create
# ============================================================================

def create_job(
    db: Session,
    *,
    asset_id: str,
    action: str,
    created_by: str,
    vulnerability_id: str | None = None,
    note: str | None = None,
) -> RemediationJob:
    """Open a new remediation job in ``pending_approval``.

    Validates that the asset exists, the optional vuln belongs to that asset,
    and the action is supported by policy. The AWX template id and the
    ``requested_payload`` are filled in here so policy decisions are recorded
    on the job row at creation time, not deferred to launch time.
    """
    # 1. Validate asset.
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise RemediationError(f"Asset {asset_id!r} not found.")

    # 2. Validate vulnerability (if given) belongs to that asset.
    vuln: Vulnerability | None = None
    if vulnerability_id is not None:
        vuln = db.get(Vulnerability, vulnerability_id)
        if vuln is None:
            raise RemediationError(f"Vulnerability {vulnerability_id!r} not found.")
        if vuln.asset_id != asset.id:
            raise RemediationError(
                "Vulnerability does not belong to the specified asset."
            )

    # 3. Resolve policy.
    if action not in _KNOWN_ACTIONS:
        raise RemediationError(
            f"Unknown remediation action {action!r}. "
            f"Known actions: {list(_KNOWN_ACTIONS)}"
        )
    template_id = _template_id_for(action)
    if template_id is None:
        raise RemediationError(
            f"No AWX template configured for action {action!r}. "
            f"Set AWX_TEMPLATE_{action.upper()} in the environment."
        )

    # 4. Build the row. extra_vars is computed now (with placeholders for
    #    fields like pa_job_id that don't exist yet) and patched at launch.
    job = RemediationJob(
        asset_id=asset.id,
        vulnerability_id=vuln.id if vuln else None,
        engine="ansible_awx",
        action=action,
        status="pending_approval",
        created_by=created_by,
        awx_job_template_id=template_id,
        requested_payload=_build_extra_vars(
            # The job doesn't have an id yet (Python-side default kicks in on
            # flush). We capture extra_vars without the platform metadata
            # at creation; launch_job patches it with the real job.id.
            job=RemediationJob(id="<pending>", action=action),
            asset=asset,
            vulnerability=vuln,
        ),
        error_message=None,
    )
    db.add(job)
    db.flush()  # populate job.id so the audit row can reference it

    record_audit(
        db,
        actor=created_by,
        action="remediation.job.created",
        entity_type="remediation_job",
        entity_id=job.id,
        success=True,
        context={"action": action, "asset_id": asset.id, "note": note},
    )
    db.commit()
    return job


# ============================================================================
# Lifecycle: approve
# ============================================================================

def approve_job(
    db: Session,
    *,
    job_id: str,
    approved_by: str,
    note: str | None = None,
) -> RemediationJob:
    """Move a job from ``pending_approval`` to ``approved``.

    Enforces Separation of Duties: the user who *created* the job cannot
    also approve it. The caller (route layer) supplies ``approved_by`` from
    the authenticated user, so the frontend cannot bypass this by faking the
    field.
    """
    job = _get_or_404(db, job_id)
    _expect_status(job, "pending_approval")

    if approved_by == job.created_by:
        raise RemediationError(
            "Cannot approve a remediation job you created yourself "
            "(separation of duties)."
        )

    job.status = "approved"
    job.approved_by = approved_by
    job.approved_at = _now()

    record_audit(
        db,
        actor=approved_by,
        action="remediation.job.approved",
        entity_type="remediation_job",
        entity_id=job.id,
        success=True,
        context={"note": note},
    )
    db.commit()
    return job


# ============================================================================
# Lifecycle: launch
# ============================================================================

async def launch_job(
    db: Session,
    awx: AnsibleClient,
    *,
    job_id: str,
    actor: str = "system",
) -> RemediationJob:
    """Move a job from ``approved`` to ``running`` by hitting AWX.

    Updates ``requested_payload`` with the real ``job.id`` (only known after
    creation) so AWX-side logs correlate to platform records.
    """
    job = _get_or_404(db, job_id)
    _expect_status(job, "approved")

    if job.awx_job_template_id is None:
        raise RemediationError(
            "Job has no AWX template id set; cannot launch (policy mismatch)."
        )

    asset = db.get(Asset, job.asset_id)
    vuln = db.get(Vulnerability, job.vulnerability_id) if job.vulnerability_id else None
    if asset is None:
        raise RemediationError("Asset for this job has been removed.")

    # Patch in the real job.id now that it exists.
    extra_vars = _build_extra_vars(job, asset, vuln)
    job.requested_payload = extra_vars

    try:
        launch_response = await awx.launch_job_template(
            job.awx_job_template_id,
            extra_vars=extra_vars,
        )
    except AnsibleError as exc:
        job.status = "failed"
        job.error_message = f"AWX launch failed: {exc}"
        record_audit(
            db, actor=actor,
            action="remediation.job.launched",
            entity_type="remediation_job",
            entity_id=job.id,
            success=False,
            context={"error": str(exc)},
        )
        db.commit()
        raise

    awx_job_id = extract_job_id(launch_response)
    job.awx_job_id = awx_job_id
    job.status = "running"
    job.error_message = None

    record_audit(
        db, actor=actor,
        action="remediation.job.launched",
        entity_type="remediation_job",
        entity_id=job.id,
        success=True,
        context={"awx_job_id": awx_job_id, "template_id": job.awx_job_template_id},
    )
    db.commit()
    return job


# ============================================================================
# Lifecycle: refresh status from AWX
# ============================================================================

async def refresh_job(
    db: Session,
    awx: AnsibleClient,
    *,
    job_id: str,
    actor: str = "system",
) -> RemediationJob:
    """Pull the AWX-side status and translate it to our vocabulary.

    Idempotent: calling refresh on a finished job is a no-op (the AWX status
    won't change). Refresh is only meaningful while ``status == "running"``;
    earlier statuses raise, later statuses just return.
    """
    job = _get_or_404(db, job_id)

    # Terminal states return as-is, no need to bother AWX.
    if job.status in {"verified_fixed", "failed", "cancelled"}:
        return job

    if job.status not in {"running", "verification_pending"}:
        raise RemediationError(
            f"Job {job.id} status {job.status!r} is not refreshable."
        )

    if job.awx_job_id is None:
        raise RemediationError("Job has no AWX job id; nothing to refresh.")

    try:
        awx_job = await awx.get_job(job.awx_job_id)
    except AnsibleError as exc:
        record_audit(
            db, actor=actor,
            action="remediation.job.refreshed",
            entity_type="remediation_job",
            entity_id=job.id,
            success=False,
            context={"error": str(exc)},
        )
        db.commit()
        raise

    awx_status = (awx_job.get("status") or "").lower()
    new_status = _AWX_TO_PLATFORM_STATUS.get(awx_status, job.status)

    job.result_payload = awx_job
    if awx_status in {"failed", "error"}:
        job.error_message = awx_job.get("job_explanation") or "AWX reported failure."
    job.status = new_status

    record_audit(
        db, actor=actor,
        action="remediation.job.refreshed",
        entity_type="remediation_job",
        entity_id=job.id,
        success=True,
        context={"awx_status": awx_status, "platform_status": new_status},
    )
    db.commit()
    return job


# ============================================================================
# Lifecycle: verify (Wazuh confirms the CVE is actually gone)
# ============================================================================

async def verify_job(
    db: Session,
    wazuh: WazuhClient,
    *,
    job_id: str,
    actor: str = "system",
) -> RemediationJob:
    """Move from ``verification_pending`` to ``verified_fixed`` (or ``failed``)
    based on Wazuh's current view of the asset.

    Only meaningful for jobs that target a specific vulnerability. Asset-wide
    jobs (``vulnerability_id is None``) cannot be auto-verified — they sit in
    ``verification_pending`` until an operator manually confirms via a future
    "confirm" endpoint.
    """
    job = _get_or_404(db, job_id)
    _expect_status(job, "verification_pending")

    if job.vulnerability_id is None:
        raise RemediationError(
            "Cannot auto-verify a job without a specific vulnerability target."
        )

    vuln = db.get(Vulnerability, job.vulnerability_id)
    if vuln is None:
        raise RemediationError("Targeted vulnerability has been removed; cannot verify.")

    asset = db.get(Asset, vuln.asset_id)
    if asset is None:
        raise RemediationError("Asset has been removed; cannot verify.")

    try:
        raw_vulns = await wazuh.list_vulnerabilities(asset.wazuh_agent_id)
    except WazuhError as exc:
        record_audit(
            db, actor=actor,
            action="remediation.job.verified",
            entity_type="remediation_job",
            entity_id=job.id,
            success=False,
            context={"error": str(exc)},
        )
        db.commit()
        raise

    seen: set[tuple[str | None, str | None]] = set()
    for r in raw_vulns:
        n = normalize_vulnerability(r)
        seen.add((n.get("cve"), n.get("package_name")))

    still_present = (vuln.cve, vuln.package_name) in seen

    if still_present:
        job.status = "failed"
        job.error_message = (
            "Wazuh still reports the vulnerability after AWX completed. "
            "The playbook ran but the CVE was not actually fixed."
        )
        record_audit(
            db, actor=actor,
            action="remediation.job.verified",
            entity_type="remediation_job",
            entity_id=job.id,
            success=False,
            context={"cve": vuln.cve, "package": vuln.package_name},
        )
    else:
        # Verified gone. Mirror the state on the vulnerability row too so the
        # /vulnerabilities views show it as fixed without waiting for the next
        # full sync.
        vuln.status = "fixed"
        job.status = "verified_fixed"
        record_audit(
            db, actor=actor,
            action="remediation.job.verified",
            entity_type="remediation_job",
            entity_id=job.id,
            success=True,
            context={"cve": vuln.cve, "package": vuln.package_name},
        )

    db.commit()
    return job
