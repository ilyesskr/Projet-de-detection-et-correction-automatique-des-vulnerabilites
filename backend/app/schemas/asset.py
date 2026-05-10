"""Asset API schemas — what the /assets routes accept and return."""

from datetime import datetime

from app.schemas.common import ORMModel


class AssetRead(ORMModel):
    """Public view of an asset.

    Deliberately omits ``raw_wazuh``: the raw payload can be kilobytes of
    nested data per asset and is irrelevant to list views. If a "detailed"
    view is ever needed, expose it via a separate schema rather than fattening
    every /assets response.
    """

    id: str
    wazuh_agent_id: str
    hostname: str | None = None
    ip_address: str | None = None
    os_name: str | None = None
    os_version: str | None = None
    os_platform: str | None = None
    agent_version: str | None = None
    status: str | None = None
    last_seen: datetime | None = None
    created_at: datetime
    updated_at: datetime
