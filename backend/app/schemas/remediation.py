"""Remediation API schemas — create / approve / read shapes for jobs."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

# Documented vocabularies. The model column is a free string so the DB never
# blocks a new action introduced by policy; these Literals enforce the
# vocabulary at the API edge.
RemediationAction = Literal[
    "package_update",
    "windows_update",
    "service_restart",
    "config_change",
]
RemediationStatus = Literal[
    "pending_approval",
    "approved",
    "running",
    "verification_pending",
    "verified_fixed",
    "failed",
    "cancelled",
]


class RemediationJobCreate(BaseModel):
    """Create a new remediation request.

    Deliberately *narrow*: the user picks the asset, optional CVE, and the
    semantic action. The backend's policy layer chooses the AWX job template
    and builds the extra_vars payload — never trust the client to set those.
    ``created_by`` is derived from the authenticated user (JWT) and never
    accepted from the request body.
    """

    asset_id: str
    vulnerability_id: str | None = None
    action: RemediationAction
    note: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional human-readable reason for the request.",
    )


class RemediationJobApprove(BaseModel):
    """Approve a pending job.

    Approval is the gate before launch. The backend records *who* approved
    and *when* in the corresponding ``RemediationJob`` row, using the
    authenticated user as the approver — not a value from the request body.
    """

    note: str | None = Field(default=None, max_length=2000)


class RemediationJobRead(ORMModel):
    """Public view of a remediation job, including AWX coordinates and result."""

    id: str
    asset_id: str
    vulnerability_id: str | None = None

    engine: str
    action: str
    status: str

    created_by: str
    approved_by: str | None = None
    approved_at: datetime | None = None

    awx_job_template_id: int | None = None
    awx_job_id: int | None = None

    requested_payload: dict[str, Any] | None = None
    result_payload: dict[str, Any] | None = None
    error_message: str | None = None

    created_at: datetime
    updated_at: datetime
