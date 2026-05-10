"""RemediationJob ORM model — one row per correction request lifecycle."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RemediationJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "remediation_jobs"

    # An asset must exist for the job to make sense; deleting an asset that
    # still has jobs is blocked at the DB level (RESTRICT) to preserve the
    # audit trail. Use soft-delete on the application side instead.
    asset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assets.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    # Optional: a job can be raised for an asset without targeting a single
    # CVE (e.g., "apply latest patches"). If the underlying vulnerability row
    # is later purged, we keep the job for history with vulnerability_id set
    # to NULL.
    vulnerability_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("vulnerabilities.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # Execution backend. Today: "ansible_awx". "manual" is reserved for jobs
    # closed out-of-band (e.g., the operator fixed it by hand and recorded it).
    engine: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ansible_awx",
    )

    # Kind of fix: "package_update", "windows_update", "service_restart", ...
    action: Mapped[str] = mapped_column(String(64), nullable=False)

    # Lifecycle:
    #   pending_approval -> approved -> running -> verification_pending -> verified_fixed
    #                                          \-> failed / cancelled
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending_approval", index=True,
    )

    # Provenance. ``created_by`` and ``approved_by`` are free strings today
    # (email / username) and will become FKs to a users table when user
    # accounts are introduced.
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # AWX coordinates. Template chosen by backend policy; job id assigned by
    # AWX when the launch succeeds.
    awx_job_template_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    awx_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Payloads: ``requested_payload`` is what we sent AWX as extra_vars;
    # ``result_payload`` is what AWX returned (status, stdout snippet, ...).
    requested_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Free-text reason a job failed. Surfaced to the frontend.
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return (
            f"<RemediationJob id={self.id} status={self.status} "
            f"awx_job={self.awx_job_id}>"
        )
