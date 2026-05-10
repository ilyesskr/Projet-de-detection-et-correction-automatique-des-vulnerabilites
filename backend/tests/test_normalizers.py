"""Pure unit tests for ``services.normalizers``.

Pure functions, no I/O — fast and trivially robust to upstream Wazuh changes.
"""

from datetime import datetime

from app.services.normalizers import (
    _normalize_severity,
    _parse_datetime,
    extract_items,
    extract_total,
    normalize_agent,
    normalize_vulnerability,
)


# ----- envelope ------------------------------------------------------------

def test_extract_items_pulls_affected_items():
    payload = {"data": {"affected_items": [{"id": "1"}, {"id": "2"}], "total_affected_items": 2}}
    assert extract_items(payload) == [{"id": "1"}, {"id": "2"}]
    assert extract_total(payload) == 2


def test_extract_items_safe_on_missing_envelope():
    assert extract_items(None) == []
    assert extract_items({}) == []
    assert extract_items({"data": None}) == []
    assert extract_total(None) == 0
    assert extract_total({"data": {}}) == 0


# ----- severity ------------------------------------------------------------

def test_severity_aliases_to_known_buckets():
    assert _normalize_severity("Critical") == "critical"
    assert _normalize_severity("HIGH") == "high"
    assert _normalize_severity("important") == "high"
    assert _normalize_severity("Moderate") == "medium"
    assert _normalize_severity("Negligible") == "low"
    assert _normalize_severity("info") == "low"


def test_severity_unknowns_fall_through():
    assert _normalize_severity(None) == "unknown"
    assert _normalize_severity("") == "unknown"
    assert _normalize_severity("untriaged") == "unknown"
    assert _normalize_severity("made-up-thing") == "unknown"


# ----- datetime ------------------------------------------------------------

def test_parse_datetime_handles_z_suffix():
    parsed = _parse_datetime("2026-05-08T10:00:00Z")
    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed.year == 2026


def test_parse_datetime_handles_offset():
    parsed = _parse_datetime("2026-05-08T10:00:00+00:00")
    assert parsed is not None
    assert parsed.tzinfo is not None


def test_parse_datetime_returns_none_for_garbage():
    assert _parse_datetime(None) is None
    assert _parse_datetime("") is None
    assert _parse_datetime("not a date") is None
    assert _parse_datetime(12345) is None  # wrong type


def test_parse_datetime_passes_through_existing_datetime():
    dt = datetime(2026, 1, 1)
    assert _parse_datetime(dt) is dt


# ----- normalize_agent -----------------------------------------------------

def test_normalize_agent_full_payload():
    raw = {
        "id": "001", "name": "debian", "ip": "192.168.122.53",
        "status": "active", "version": "Wazuh v4.8.0",
        "lastKeepAlive": "2026-05-08T10:00:00Z",
        "os": {"name": "Debian", "version": "12", "platform": "debian"},
    }
    out = normalize_agent(raw)
    assert out["wazuh_agent_id"] == "001"
    assert out["hostname"] == "debian"
    assert out["ip_address"] == "192.168.122.53"
    assert out["os_name"] == "Debian"
    assert out["os_platform"] == "debian"
    assert out["status"] == "active"
    assert out["last_seen"] is not None
    assert out["raw_wazuh"] is raw


def test_normalize_agent_tolerates_missing_os():
    raw = {"id": "002", "name": "naked"}
    out = normalize_agent(raw)
    assert out["os_name"] is None
    assert out["os_platform"] is None
    assert out["last_seen"] is None


# ----- normalize_vulnerability --------------------------------------------

def test_normalize_vulnerability_nested_shape():
    raw = {
        "cve": "CVE-2024-1234", "severity": "High",
        "package": {"name": "openssl", "version": "1.1.1"},
        "fixed_version": "1.1.1k",
        "score": {"base": 7.5},
        "published": "2024-01-15T00:00:00Z",
    }
    out = normalize_vulnerability(raw)
    assert out["cve"] == "CVE-2024-1234"
    assert out["severity"] == "high"
    assert out["package_name"] == "openssl"
    assert out["installed_version"] == "1.1.1"
    assert out["fixed_version"] == "1.1.1k"
    assert out["cvss_score"] == 7.5


def test_normalize_vulnerability_flat_shape():
    raw = {
        "cve_id": "CVE-2024-9999", "severity": "critical",
        "package_name": "curl", "package_version": "7.0",
        "fix_version": "7.88", "cvss3_score": "9.8",  # string, must coerce
    }
    out = normalize_vulnerability(raw)
    assert out["cve"] == "CVE-2024-9999"
    assert out["severity"] == "critical"
    assert out["package_name"] == "curl"
    assert out["fixed_version"] == "7.88"
    assert out["cvss_score"] == 9.8


def test_normalize_vulnerability_wazuh_indexer_shape():
    raw = {
        "agent": {"id": "001", "name": "debian-agent"},
        "package": {"name": "openssl", "version": "1.1.1w"},
        "vulnerability": {
            "id": "CVE-2024-1234",
            "severity": "High",
            "score": {"base": 7.5},
            "published_at": "2024-01-15T00:00:00Z",
            "description": "Example OpenSSL vulnerability.",
        },
    }
    out = normalize_vulnerability(raw)
    assert out["cve"] == "CVE-2024-1234"
    assert out["title"] == "Example OpenSSL vulnerability."
    assert out["severity"] == "high"
    assert out["package_name"] == "openssl"
    assert out["installed_version"] == "1.1.1w"
    assert out["cvss_score"] == 7.5
    assert out["published_at"] is not None


def test_normalize_vulnerability_does_not_set_asset_id():
    raw = {"cve": "CVE-2024-A", "severity": "low"}
    out = normalize_vulnerability(raw)
    assert "asset_id" not in out
