"""Asset ORM model — one row per Wazuh agent."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Asset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "assets"

    # Stable link back to Wazuh. Guaranteed unique by sync logic — the unique
    # constraint at the DB level enforces it as a hard invariant.
    wazuh_agent_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False,
    )

    # Identity fields for humans / playbooks. ip_address sized for IPv6.
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # OS facts — used by the remediation policy to pick Linux vs Windows
    # playbooks and decide which fixes are applicable.
    os_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    os_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    os_platform: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Wazuh's reported agent state. Kept as a free string because the
    # vocabulary varies across Wazuh versions ("active", "disconnected",
    # "never_connected", "pending", ...).
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # When Wazuh last received a heartbeat from the agent. Distinct from
    # ``updated_at``, which is when *we* last touched the row.
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # Original Wazuh payload, preserved verbatim for debugging and for fields
    # we haven't promoted to typed columns yet.
    raw_wazuh: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return (
            f"<Asset id={self.id} hostname={self.hostname!r} "
            f"agent={self.wazuh_agent_id}>"
        )
