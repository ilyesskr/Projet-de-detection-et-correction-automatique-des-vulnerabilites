"""Sync flow tests against the route layer with a fake Wazuh client."""

from app.models import Asset, AuditLog, Vulnerability


def test_sync_agents_creates_then_reupdates(client, auth_header, fake_wazuh, db):
    # === Round 1: empty DB, two agents reported by Wazuh ===
    fake_wazuh.agents = [
        {"id": "001", "name": "debian", "ip": "192.168.122.53",
         "os": {"name": "Debian", "platform": "debian"},
         "status": "active", "version": "4.8.0",
         "lastKeepAlive": "2026-05-08T10:00:00Z"},
        {"id": "002", "name": "windows",
         "os": {"name": "Windows", "platform": "windows"},
         "status": "active", "version": "4.8.0"},
    ]

    r = client.post("/api/v1/sync/wazuh/agents", headers=auth_header)
    assert r.status_code == 200
    summary = r.json()
    assert summary["created"] == 2
    assert summary["updated"] == 0
    assert summary["errors"] == []

    assets = db.query(Asset).all()
    assert len(assets) == 2
    assert {a.hostname for a in assets} == {"debian", "windows"}

    # === Round 2: identical payload, no diffs -> all unchanged ===
    r2 = client.post("/api/v1/sync/wazuh/agents", headers=auth_header)
    assert r2.status_code == 200
    s2 = r2.json()
    assert s2["created"] == 0
    assert s2["unchanged"] == 2

    # === Round 3: change debian's IP -> exactly one updated ===
    fake_wazuh.agents[0]["ip"] = "192.168.122.99"
    r3 = client.post("/api/v1/sync/wazuh/agents", headers=auth_header)
    s3 = r3.json()
    assert s3["updated"] == 1
    assert s3["unchanged"] == 1


def test_sync_vulnerabilities_marks_absent_as_fixed(
    client, auth_header, fake_wazuh, db,
):
    """The Wazuh-side verification flow: a CVE that disappears from a later
    sync gets flipped to ``fixed`` automatically."""
    fake_wazuh.agents = [
        {"id": "001", "name": "debian",
         "os": {"name": "Debian", "platform": "debian"},
         "status": "active"},
    ]
    fake_wazuh.vulns_by_agent = {
        "001": [
            {"cve": "CVE-2024-A", "severity": "High",
             "package": {"name": "openssl", "version": "1.1.1"}},
            {"cve": "CVE-2024-B", "severity": "Medium",
             "package": {"name": "curl", "version": "7.0"}},
        ],
    }

    # Sync agents first so vuln sync has assets to iterate.
    client.post("/api/v1/sync/wazuh/agents", headers=auth_header)
    r = client.post("/api/v1/sync/wazuh/vulnerabilities", headers=auth_header)
    assert r.status_code == 200
    assert r.json()["created"] == 2

    # Drop CVE-2024-B from Wazuh and resync.
    fake_wazuh.vulns_by_agent["001"] = fake_wazuh.vulns_by_agent["001"][:1]
    r2 = client.post("/api/v1/sync/wazuh/vulnerabilities", headers=auth_header)
    s2 = r2.json()
    assert s2["marked_fixed"] == 1

    db.expire_all()
    by_status = {v.cve: v.status for v in db.query(Vulnerability).all()}
    assert by_status == {"CVE-2024-A": "open", "CVE-2024-B": "fixed"}


def test_sync_when_wazuh_is_down_returns_502(client, auth_header, fake_wazuh):
    fake_wazuh.health_ok = False
    r = client.post("/api/v1/sync/wazuh/agents", headers=auth_header)
    assert r.status_code == 502
    assert "wazuh" in r.json()["detail"].lower()


def test_sync_audit_rows_written(client, auth_header, fake_wazuh, db):
    fake_wazuh.agents = [
        {"id": "001", "name": "x", "os": {"platform": "debian"}, "status": "active"},
    ]
    client.post("/api/v1/sync/wazuh/agents", headers=auth_header)
    client.post("/api/v1/sync/wazuh/vulnerabilities", headers=auth_header)

    actions = {a.action for a in db.query(AuditLog).all()}
    assert "sync.wazuh.agents" in actions
    assert "sync.wazuh.vulnerabilities" in actions
