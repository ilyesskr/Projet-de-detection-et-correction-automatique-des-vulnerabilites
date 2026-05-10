"""Smoke tests for GET /api/v1/dashboard/summary."""

from app.core.security import create_access_token, hash_password
from app.models import (
    Asset,
    RemediationJob,
    User,
    Vulnerability,
    user_asset_scope_table,
)


# ----- Auth ---------------------------------------------------------------

def test_summary_requires_auth(client):
    r = client.get("/api/v1/dashboard/summary")
    assert r.status_code == 401


# ----- Shape --------------------------------------------------------------

def test_summary_returns_well_formed_empty_payload(client, auth_header, fake_wazuh, fake_awx):
    r = client.get("/api/v1/dashboard/summary", headers=auth_header)
    assert r.status_code == 200
    body = r.json()

    assert body == {
        "assets_total": 0,
        "assets_active": 0,
        "vulns_open_by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "jobs_by_status": {
            "pending_approval": 0,
            "approved": 0,
            "running": 0,
            "verification_pending": 0,
            "verified_fixed": 0,
            "failed": 0,
            "cancelled": 0,
        },
        "wazuh_reachable": True,
        "awx_reachable": True,
    }


# ----- Aggregation --------------------------------------------------------

def test_summary_counts_assets_vulns_and_jobs(
    client, auth_header, db, fake_wazuh, fake_awx,
):
    a1 = Asset(wazuh_agent_id="001", hostname="h1", status="active")
    a2 = Asset(wazuh_agent_id="002", hostname="h2", status="disconnected")
    db.add_all([a1, a2])
    db.commit()
    db.refresh(a1)
    db.refresh(a2)

    db.add_all([
        Vulnerability(asset_id=a1.id, cve="CVE-A", severity="critical"),
        Vulnerability(asset_id=a1.id, cve="CVE-B", severity="high"),
        Vulnerability(asset_id=a2.id, cve="CVE-C", severity="high"),
        Vulnerability(asset_id=a2.id, cve="CVE-D", severity="low", status="fixed"),
        # "unknown" must not crash even though it has no bucket.
        Vulnerability(asset_id=a2.id, cve="CVE-E", severity="unknown"),
    ])
    db.add_all([
        RemediationJob(asset_id=a1.id, action="package_update", status="pending_approval", created_by="alice"),
        RemediationJob(asset_id=a1.id, action="package_update", status="approved", created_by="alice"),
        RemediationJob(asset_id=a2.id, action="package_update", status="failed", created_by="alice"),
    ])
    db.commit()

    r = client.get("/api/v1/dashboard/summary", headers=auth_header)
    assert r.status_code == 200
    body = r.json()

    assert body["assets_total"] == 2
    assert body["assets_active"] == 1
    assert body["vulns_open_by_severity"] == {
        "critical": 1, "high": 2, "medium": 0, "low": 0,
    }
    assert body["jobs_by_status"]["pending_approval"] == 1
    assert body["jobs_by_status"]["approved"] == 1
    assert body["jobs_by_status"]["failed"] == 1
    assert body["jobs_by_status"]["running"] == 0


# ----- Asset scope --------------------------------------------------------

def test_summary_respects_asset_scope_for_non_superuser(
    client, db, fake_wazuh, fake_awx,
):
    a1 = Asset(wazuh_agent_id="001", hostname="h1", status="active")
    a2 = Asset(wazuh_agent_id="002", hostname="h2", status="active")
    db.add_all([a1, a2])
    db.commit()
    db.refresh(a1)
    db.refresh(a2)

    db.add_all([
        Vulnerability(asset_id=a1.id, cve="CVE-A", severity="high"),
        Vulnerability(asset_id=a2.id, cve="CVE-B", severity="high"),
    ])
    db.commit()

    # Scoped non-superuser viewer who can see only a1.
    user = User(
        username="vince", email="vince@test.local",
        hashed_password=hash_password("x"),
        is_active=True, is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.execute(
        user_asset_scope_table.insert().values(user_id=user.id, asset_id=a1.id),
    )
    db.commit()

    token = create_access_token(user_id=user.id, username=user.username)
    r = client.get(
        "/api/v1/dashboard/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["assets_total"] == 1
    assert body["assets_active"] == 1
    assert body["vulns_open_by_severity"]["high"] == 1


# ----- Integration reachability -------------------------------------------

def test_summary_reports_wazuh_unreachable(
    client, auth_header, fake_wazuh, fake_awx,
):
    fake_wazuh.health_ok = False

    r = client.get("/api/v1/dashboard/summary", headers=auth_header)
    assert r.status_code == 200
    body = r.json()
    assert body["wazuh_reachable"] is False
    assert body["awx_reachable"] is True


def test_summary_reports_awx_unreachable(
    client, auth_header, fake_wazuh, fake_awx,
):
    fake_awx.health_ok = False

    r = client.get("/api/v1/dashboard/summary", headers=auth_header)
    assert r.status_code == 200
    body = r.json()
    assert body["wazuh_reachable"] is True
    assert body["awx_reachable"] is False
