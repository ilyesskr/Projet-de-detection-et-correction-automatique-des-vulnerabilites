"""Convert raw Wazuh JSON into the dict shape our ORM models expect.

Wazuh's response shape varies across versions, OS platforms, and even
individual vulnerability records. The normalizers absorb that variability so
the rest of the codebase only ever deals with our stable internal shape.

These functions are deliberately pure: no I/O, no DB, no logging. That makes
them trivially unit-testable from raw fixtures.
"""

from datetime import datetime
from typing import Any

# ----- Wazuh response envelope ------------------------------------------------

def extract_items(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Pull the list of records out of the standard Wazuh response envelope.

    Wazuh wraps every list endpoint in::

        {"data": {"affected_items": [...], "total_affected_items": N}, "error": 0}

    Returns ``[]`` if the envelope is missing or malformed; never raises.
    """
    if not isinstance(payload, dict):
        return []
    data = payload.get("data") or {}
    items = data.get("affected_items") or []
    return items if isinstance(items, list) else []


def extract_total(payload: dict[str, Any] | None) -> int:
    """Pull ``total_affected_items`` from a Wazuh envelope, defaulting to 0."""
    if not isinstance(payload, dict):
        return 0
    data = payload.get("data") or {}
    total = data.get("total_affected_items")
    return int(total) if isinstance(total, int) else 0


# ----- Field-level helpers ----------------------------------------------------

# Wazuh / CVE feeds use varying severity vocabularies depending on the source
# (NVD, vendor advisories, ...). Map them to our four-tier scale + "unknown".
_SEVERITY_ALIASES = {
    "critical": "critical",
    "high": "high",
    "important": "high",
    "medium": "medium",
    "moderate": "medium",
    "low": "low",
    "negligible": "low",
    "informational": "low",
    "info": "low",
    "none": "unknown",
    "untriaged": "unknown",
    "unknown": "unknown",
}


def _normalize_severity(value: Any) -> str:
    if value is None:
        return "unknown"
    key = str(value).strip().lower()
    return _SEVERITY_ALIASES.get(key, "unknown")


def _parse_datetime(value: Any) -> datetime | None:
    """Parse Wazuh ISO-8601 strings into timezone-aware datetimes.

    Returns ``None`` for missing or unparseable values so the caller never has
    to guard against bad data poisoning a whole sync run.
    """
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    # Python 3.11+ understands a trailing Z natively, but be belt-and-suspenders
    # for older inputs that may slip through.
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _coerce_float(value: Any) -> float | None:
    """Best-effort float coercion. Returns None for missing or bad input."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_dict(value: Any) -> dict[str, Any]:
    """Return ``value`` if it is a dict, otherwise an empty dict."""
    return value if isinstance(value, dict) else {}


# ----- Top-level normalizers --------------------------------------------------

def normalize_agent(raw: dict[str, Any]) -> dict[str, Any]:
    """Reshape one ``/agents`` item into an Asset row dict.

    The output matches Asset model column names verbatim so the caller can do::

        Asset(**normalize_agent(raw))

    Unknown OS substructure is tolerated; ``os_*`` columns simply stay ``None``.
    """
    os_info = raw.get("os") or {}
    return {
        "wazuh_agent_id": str(raw.get("id")) if raw.get("id") is not None else None,
        "hostname": raw.get("name"),
        "ip_address": raw.get("ip"),
        "os_name": os_info.get("name"),
        "os_version": os_info.get("version"),
        "os_platform": os_info.get("platform"),
        "agent_version": raw.get("version"),
        "status": raw.get("status"),
        "last_seen": _parse_datetime(raw.get("lastKeepAlive")),
        "raw_wazuh": raw,
    }


def normalize_vulnerability(raw: dict[str, Any]) -> dict[str, Any]:
    """Reshape one Wazuh vulnerability record into a Vulnerability row dict.

    Does NOT set ``asset_id`` — that's the caller's job (it's known from the
    iteration context). Keeps the normalizer focused on pure shape conversion.

    Defensive against the common Wazuh shapes:
    - nested:  {"package": {"name": "openssl", "version": "1.1.1"}, "score": {"base": 7.5}}
    - flat:    {"package_name": "openssl", "package_version": "1.1.1", "cvss3_score": 7.5}
    - indexer: {"package": {...}, "vulnerability": {"id": "CVE-...", "score": {"base": 7.5}}}
    """
    package = _as_dict(raw.get("package"))
    vulnerability = _as_dict(raw.get("vulnerability"))
    score = _as_dict(raw.get("score")) or _as_dict(vulnerability.get("score"))

    cvss = (
        _coerce_float(score.get("base"))
        or _coerce_float(vulnerability.get("score"))
        or _coerce_float(raw.get("cvss3_score"))
        or _coerce_float(raw.get("cvss2_score"))
        or _coerce_float(raw.get("cvss"))
    )

    return {
        "cve": (
            raw.get("cve")
            or raw.get("cve_id")
            or vulnerability.get("id")
            or vulnerability.get("cve")
        ),
        "title": (
            raw.get("title")
            or vulnerability.get("title")
            or raw.get("description")
            or vulnerability.get("description")
        ),
        "severity": _normalize_severity(
            raw.get("severity") or vulnerability.get("severity")
        ),
        "cvss_score": cvss,
        "package_name": package.get("name") or raw.get("package_name"),
        "installed_version": package.get("version") or raw.get("package_version"),
        "fixed_version": (
            raw.get("fixed_version")
            or raw.get("fix_version")
            or package.get("fixed_version")
            or vulnerability.get("fixed_version")
            or vulnerability.get("fix_version")
        ),
        "published_at": _parse_datetime(
            raw.get("published")
            or raw.get("published_at")
            or vulnerability.get("published")
            or vulnerability.get("published_at")
        ),
        "raw_wazuh": raw,
    }
