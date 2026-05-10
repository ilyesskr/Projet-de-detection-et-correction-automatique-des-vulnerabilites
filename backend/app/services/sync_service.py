"""Wazuh-to-database synchronization.

Two operations:

* ``sync_agents``: pull every Wazuh agent and upsert it as an Asset row.
* ``sync_vulnerabilities``: for each asset, pull its CVE list, upsert each
  vulnerability, and mark previously-open CVEs that are no longer reported as
  ``fixed`` (this is how Wazuh-side verification of remediation surfaces).

Both functions return a ``SyncResult`` summary and write one audit row.
Errors on individual items are collected, not raised — partial success is the
expected mode for a sync over hundreds of agents.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, Vulnerability
from app.services.audit_service import record_audit
from app.services.normalizers import normalize_agent, normalize_vulnerability
from app.services.wazuh_client import WazuhClient, WazuhError


class SyncResult(BaseModel):
    """Summary of a sync run, returned by the route and stored in the audit row."""

    created: int = 0
    updated: int = 0
    unchanged: int = 0
    marked_fixed: int = 0
    skipped: int = 0
    errors: list[str] = []


# ----- internal helpers -----------------------------------------------------

def _to_naive_utc(dt: datetime) -> datetime:
    """Drop tzinfo by converting to UTC first. Naive datetimes pass through."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _equal_for_dirty_check(a: Any, b: Any) -> bool:
    """Equality that treats the same instant as equal regardless of tzinfo.

    Why this exists: SQLAlchemy's SQLite dialect strips tzinfo on read while
    PostgreSQL preserves it. Without this normalization, the same instant
    could compare unequal after a round-trip on SQLite, causing spurious
    "updated" verdicts during sync.
    """
    if isinstance(a, datetime) and isinstance(b, datetime):
        return _to_naive_utc(a) == _to_naive_utc(b)
    return a == b


def _apply_changes(orm_obj: Any, normalized: dict[str, Any]) -> bool:
    """Copy normalized fields onto an ORM object; return True if anything changed.

    Field-level diff so the ``updated_at`` timestamp only bumps on a real
    change. ``raw_wazuh`` is compared structurally by ``==`` on the dict,
    which is what we want — same payload means same data.
    """
    changed = False
    for field, new_value in normalized.items():
        if not _equal_for_dirty_check(getattr(orm_obj, field), new_value):
            setattr(orm_obj, field, new_value)
            changed = True
    return changed


# ----- agents ---------------------------------------------------------------

async def sync_agents(
    db: Session,
    wazuh: WazuhClient,
    *,
    actor: str = "system",
) -> SyncResult:
    """Pull all Wazuh agents and upsert into ``assets``."""
    result = SyncResult()

    try:
        raw_agents = await wazuh.list_agents()
    except WazuhError as exc:
        # Whole-run failure: write a failed audit row and re-raise so the route
        # surfaces an HTTP error to the caller.
        record_audit(
            db,
            actor=actor,
            action="sync.wazuh.agents",
            success=False,
            context={"error": str(exc)},
        )
        db.commit()
        raise

    for raw in raw_agents:
        try:
            normalized = normalize_agent(raw)
            wazuh_agent_id = normalized.get("wazuh_agent_id")
            if not wazuh_agent_id:
                result.skipped += 1
                continue

            existing = db.execute(
                select(Asset).where(Asset.wazuh_agent_id == wazuh_agent_id)
            ).scalar_one_or_none()

            if existing is None:
                db.add(Asset(**normalized))
                result.created += 1
            else:
                if _apply_changes(existing, normalized):
                    result.updated += 1
                else:
                    result.unchanged += 1
        except Exception as exc:  # pragma: no cover - defensive
            result.errors.append(f"agent {raw.get('id', '?')}: {exc}")
            result.skipped += 1

    db.commit()

    record_audit(
        db,
        actor=actor,
        action="sync.wazuh.agents",
        success=not result.errors,
        context=result.model_dump(),
    )
    db.commit()
    return result


# ----- vulnerabilities ------------------------------------------------------

async def sync_vulnerabilities(
    db: Session,
    wazuh: WazuhClient,
    *,
    actor: str = "system",
) -> SyncResult:
    """Pull every asset's CVE list, upsert, and flip absent CVEs to ``fixed``.

    Per-asset failures are recorded in ``errors`` and we move on. The
    "mark as fixed" sweep only runs for assets whose CVE fetch succeeded —
    a Wazuh failure must NOT cause the platform to falsely declare CVEs
    fixed.
    """
    result = SyncResult()
    assets = db.execute(select(Asset)).scalars().all()

    for asset in assets:
        try:
            raw_vulns = await wazuh.list_vulnerabilities(asset.wazuh_agent_id)
        except WazuhError as exc:
            result.errors.append(f"asset {asset.id} fetch failed: {exc}")
            continue  # do NOT touch this asset's existing CVEs

        seen_keys: set[tuple[str, str | None]] = set()

        for raw in raw_vulns:
            try:
                normalized = normalize_vulnerability(raw)
                cve = normalized.get("cve")
                if not cve:
                    result.skipped += 1
                    continue

                package = normalized.get("package_name")
                seen_keys.add((cve, package))

                existing = db.execute(
                    select(Vulnerability).where(
                        Vulnerability.asset_id == asset.id,
                        Vulnerability.cve == cve,
                        Vulnerability.package_name == package,
                    )
                ).scalar_one_or_none()

                if existing is None:
                    db.add(Vulnerability(
                        asset_id=asset.id,
                        status="open",
                        **normalized,
                    ))
                    result.created += 1
                else:
                    changed = _apply_changes(existing, normalized)
                    # If a previously-fixed CVE re-appears, it's open again.
                    if existing.status != "open":
                        existing.status = "open"
                        changed = True
                    if changed:
                        result.updated += 1
                    else:
                        result.unchanged += 1
            except Exception as exc:  # pragma: no cover - defensive
                result.errors.append(
                    f"asset {asset.id} cve {raw.get('cve', '?')}: {exc}"
                )
                result.skipped += 1

        # Sweep: any open CVE for this asset that we *didn't* see this run
        # has been remediated (Wazuh no longer reports it).
        previously_open = db.execute(
            select(Vulnerability).where(
                Vulnerability.asset_id == asset.id,
                Vulnerability.status == "open",
            )
        ).scalars().all()
        for v in previously_open:
            if (v.cve, v.package_name) not in seen_keys:
                v.status = "fixed"
                result.marked_fixed += 1

    db.commit()

    record_audit(
        db,
        actor=actor,
        action="sync.wazuh.vulnerabilities",
        success=not result.errors,
        context=result.model_dump(),
    )
    db.commit()
    return result
