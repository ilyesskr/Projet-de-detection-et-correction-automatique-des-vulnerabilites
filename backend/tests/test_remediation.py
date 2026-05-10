"""Remediation lifecycle tests against the route layer with fake AWX + Wazuh.

Note on identity: ``auth_header`` is alice's bearer token (creator),
``approver_header`` is bob's bearer token (approver). Using two distinct
identities keeps the Separation-of-Duties rule happy on the approve step.
"""

import pytest

from app.models import Asset, AuditLog, RemediationJob, Vulnerability


@pytest.fixture
def seeded(db):
    """One asset + one vulnerability ready for a remediation flow."""
    asset = Asset(
        wazuh_agent_id="001",
        hostname="debian",
        ip_address="192.168.122.53",
        os_platform="debian",
        status="active",
    )
    db.add(asset)
    db.flush()
    vuln = Vulnerability(
        asset_id=asset.id,
        cve="CVE-2024-1234",
        package_name="openssl",
        installed_version="1.1.1",
        fixed_version="1.1.1k",
        severity="high",
        status="open",
    )
    db.add(vuln)
    db.commit()
    db.refresh(asset)
    db.refresh(vuln)
    return asset, vuln


# ============================================================================
# Happy path: create -> approve -> launch -> refresh -> verify
# ============================================================================

def test_full_lifecycle(
    client, auth_header, approver_header, fake_awx, fake_wazuh, seeded, db,
):
    asset, vuln = seeded

    # 1. CREATE (alice)
    r = client.post(
        "/api/v1/remediation/jobs",
        headers=auth_header,
        json={
            "asset_id": asset.id,
            "vulnerability_id": vuln.id,
            "action": "package_update",
        },
    )
    assert r.status_code == 201, r.text
    job = r.json()
    assert job["status"] == "pending_approval"
    assert job["awx_job_template_id"] == 10  # policy: package_update -> 10
    assert job["created_by"] == "alice"
    job_id = job["id"]

    # 2. APPROVE (bob — separation of duties)
    r = client.post(
        f"/api/v1/remediation/jobs/{job_id}/approve",
        headers=approver_header,
        json={},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"
    assert r.json()["approved_by"] == "bob"

    # 3. LAUNCH (fake AWX assigns next id 1000) — any approver/operator works.
    r = client.post(f"/api/v1/remediation/jobs/{job_id}/launch", headers=approver_header)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "running"
    assert body["awx_job_id"] == 1000
    # AWX received the policy-built extra_vars including the platform job id.
    assert fake_awx.launches == [(10, body["requested_payload"])]
    assert body["requested_payload"]["pa_job_id"] == job_id
    assert body["requested_payload"]["cve"] == "CVE-2024-1234"

    # 4. REFRESH (fake AWX says successful -> verification_pending)
    r = client.post(f"/api/v1/remediation/jobs/{job_id}/refresh", headers=approver_header)
    assert r.status_code == 200
    assert r.json()["status"] == "verification_pending"

    # 5. VERIFY (fake Wazuh no longer reports the CVE)
    fake_wazuh.vulns_by_agent = {"001": []}
    r = client.post(f"/api/v1/remediation/jobs/{job_id}/verify", headers=approver_header)
    assert r.status_code == 200
    assert r.json()["status"] == "verified_fixed"

    # The vulnerability row was mirrored to "fixed" too — operators see it
    # without waiting for the next full sync.
    db.expire_all()
    assert db.get(Vulnerability, vuln.id).status == "fixed"


# ============================================================================
# Failed verification: AWX ran but Wazuh still sees the CVE
# ============================================================================

def test_verify_marks_failed_if_cve_still_present(
    client, auth_header, approver_header, fake_awx, fake_wazuh, seeded, db,
):
    asset, vuln = seeded

    # Drive the job to verification_pending the fast way: create+approve+launch+refresh.
    job_id = client.post(
        "/api/v1/remediation/jobs",
        headers=auth_header,
        json={"asset_id": asset.id, "vulnerability_id": vuln.id,
              "action": "package_update"},
    ).json()["id"]
    client.post(f"/api/v1/remediation/jobs/{job_id}/approve",
                headers=approver_header, json={})
    client.post(f"/api/v1/remediation/jobs/{job_id}/launch", headers=approver_header)
    client.post(f"/api/v1/remediation/jobs/{job_id}/refresh", headers=approver_header)

    # Wazuh still reports the CVE -> verification fails.
    fake_wazuh.vulns_by_agent = {"001": [
        {"cve": "CVE-2024-1234", "severity": "High",
         "package": {"name": "openssl", "version": "1.1.1"}},
    ]}
    r = client.post(f"/api/v1/remediation/jobs/{job_id}/verify", headers=approver_header)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "failed"
    assert "still reports" in (body["error_message"] or "")


# ============================================================================
# State-machine errors -> 4xx
# ============================================================================

def test_create_with_unknown_asset_is_404(client, auth_header):
    r = client.post(
        "/api/v1/remediation/jobs",
        headers=auth_header,
        json={"asset_id": "ghost", "action": "package_update"},
    )
    # Superuser bypasses scope, so we get the service's 404 rather than 403.
    assert r.status_code == 404


def test_approve_already_approved_is_409(
    client, auth_header, approver_header, seeded,
):
    asset, _ = seeded
    job_id = client.post(
        "/api/v1/remediation/jobs",
        headers=auth_header,
        json={"asset_id": asset.id, "action": "package_update"},
    ).json()["id"]
    # First approve -> 200 (bob)
    r1 = client.post(f"/api/v1/remediation/jobs/{job_id}/approve",
                     headers=approver_header, json={})
    assert r1.status_code == 200
    # Second approve on now-approved job -> 409
    r2 = client.post(f"/api/v1/remediation/jobs/{job_id}/approve",
                     headers=approver_header, json={})
    assert r2.status_code == 409


def test_verify_without_vuln_id_is_400(
    client, auth_header, approver_header, fake_awx, fake_wazuh, seeded,
):
    asset, _ = seeded
    # Asset-wide job, no vulnerability_id
    job_id = client.post(
        "/api/v1/remediation/jobs",
        headers=auth_header,
        json={"asset_id": asset.id, "action": "package_update"},
    ).json()["id"]
    client.post(f"/api/v1/remediation/jobs/{job_id}/approve",
                headers=approver_header, json={})
    client.post(f"/api/v1/remediation/jobs/{job_id}/launch", headers=approver_header)
    client.post(f"/api/v1/remediation/jobs/{job_id}/refresh", headers=approver_header)

    r = client.post(f"/api/v1/remediation/jobs/{job_id}/verify", headers=approver_header)
    assert r.status_code == 400
    assert "auto-verify" in r.text


# ============================================================================
# Audit trail: every transition writes one row
# ============================================================================

def test_audit_row_per_transition(
    client, auth_header, approver_header, fake_awx, fake_wazuh, seeded, db,
):
    asset, vuln = seeded
    job_id = client.post(
        "/api/v1/remediation/jobs",
        headers=auth_header,
        json={"asset_id": asset.id, "vulnerability_id": vuln.id,
              "action": "package_update"},
    ).json()["id"]
    client.post(f"/api/v1/remediation/jobs/{job_id}/approve",
                headers=approver_header, json={})
    client.post(f"/api/v1/remediation/jobs/{job_id}/launch", headers=approver_header)
    client.post(f"/api/v1/remediation/jobs/{job_id}/refresh", headers=approver_header)
    fake_wazuh.vulns_by_agent = {"001": []}
    client.post(f"/api/v1/remediation/jobs/{job_id}/verify", headers=approver_header)

    actions = [
        a.action
        for a in db.query(AuditLog)
                  .filter(AuditLog.entity_id == job_id)
                  .order_by(AuditLog.created_at)
                  .all()
    ]
    assert actions == [
        "remediation.job.created",
        "remediation.job.approved",
        "remediation.job.launched",
        "remediation.job.refreshed",
        "remediation.job.verified",
    ]
