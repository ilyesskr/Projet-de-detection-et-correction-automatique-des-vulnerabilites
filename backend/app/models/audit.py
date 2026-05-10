"""AuditLog ORM model — append-only record of platform actions."""

from sqlalchemy import JSON, Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    # Who did it. "system" for backend-initiated events (sync runs, scheduled
    # jobs); user identifier (email / username) for human actions.
    actor: Mapped[str] = mapped_column(String(128), nullable=False)

    # Dotted action name. Conventions:
    #   sync.wazuh.agents
    #   sync.wazuh.vulnerabilities
    #   remediation.job.created / .approved / .launched / .completed
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # The thing affected. Both nullable because some events aren't tied to a
    # single row (a sync run touches many assets — entity_type stays NULL).
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Did the action succeed? Lets the frontend filter for failures quickly.
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Anything extra: counts (items_synced=42), error messages, payload diffs.
    # Named ``context`` rather than ``metadata`` because ``metadata`` is taken
    # by SQLAlchemy's declarative Base.
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return f"<AuditLog id={self.id} action={self.action} actor={self.actor}>"
