"""Audit-log writer.

Append-only by convention: callers write records but never delete or update
existing ones. The function does not commit on its own — the caller controls
the transaction so that the audited business action and its audit row land
together (or roll back together).
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def record_audit(
    db: Session,
    *,
    actor: str,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    success: bool = True,
    context: dict[str, Any] | None = None,
) -> AuditLog:
    """Insert one row into ``audit_logs``.

    The caller is responsible for ``db.commit()`` so that the audit row and
    whatever business change it describes are committed atomically.

    Conventions for ``action``:
      sync.wazuh.agents
      sync.wazuh.vulnerabilities
      remediation.job.created
      remediation.job.approved
      remediation.job.launched
      remediation.job.completed
    """
    log = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        success=success,
        context=context,
    )
    db.add(log)
    return log
