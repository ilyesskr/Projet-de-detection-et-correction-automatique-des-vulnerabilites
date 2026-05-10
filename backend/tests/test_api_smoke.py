"""End-to-end smoke tests for the routes layer.

Hits each endpoint via FastAPI's TestClient against in-memory SQLite. Covers
the JWT auth surface, listings, filters, 404s, and Pydantic 422 validation.
"""

from app.models import Asset, Vulnerability


# ----- Public health -------------------------------------------------------

def test_public_health_is_open(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ----- JWT gate ------------------------------------------------------------

def test_protected_route_requires_token(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 401


def test_protected_route_rejects_bad_token(client):
    r = client.get(
        "/api/v1/health",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert r.status_code == 401


def test_protected_route_accepts_good_token(client, auth_header):
    r = client.get("/api/v1/health", headers=auth_header)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ----- Empty listings ------------------------------------------------------

def test_empty_listings_return_well_formed_pages(client, auth_header):
    for path in (
        "/api/v1/assets",
        "/api/v1/vulnerabilities",
        "/api/v1/remediation/jobs",
        "/api/v1/audit-logs",
    ):
        r = client.get(path, headers=auth_header)
        assert r.status_code == 200, path
        body = r.json()
        assert body == {"items": [], "total": 0, "limit": 50, "offset": 0}, path


# ----- Listing with seeded data --------------------------------------------

def test_assets_listing_returns_seeded_rows(client, auth_header, db):
    db.add_all([
        Asset(wazuh_agent_id="001", hostname="debian"),
        Asset(wazuh_agent_id="002", hostname="windows"),
    ])
    db.commit()

    r = client.get("/api/v1/assets", headers=auth_header)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert {item["hostname"] for item in body["items"]} == {"debian", "windows"}


def test_assets_search_filter(client, auth_header, db):
    db.add_all([
        Asset(wazuh_agent_id="001", hostname="debian-1"),
        Asset(wazuh_agent_id="002", hostname="debian-2"),
        Asset(wazuh_agent_id="003", hostname="ubuntu"),
    ])
    db.commit()

    r = client.get("/api/v1/assets?search=debian", headers=auth_header)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert all("debian" in i["hostname"] for i in body["items"])


def test_get_asset_by_id(client, auth_header, db):
    a = Asset(wazuh_agent_id="001", hostname="debian")
    db.add(a)
    db.commit()
    db.refresh(a)

    r = client.get(f"/api/v1/assets/{a.id}", headers=auth_header)
    assert r.status_code == 200
    assert r.json()["wazuh_agent_id"] == "001"


def test_get_nonexistent_asset_is_404(client, auth_header):
    r = client.get("/api/v1/assets/no-such-id", headers=auth_header)
    assert r.status_code == 404


def test_asset_vulnerabilities_subroute(client, auth_header, db):
    a = Asset(wazuh_agent_id="001", hostname="debian")
    db.add(a)
    db.commit()
    db.refresh(a)
    db.add_all([
        Vulnerability(asset_id=a.id, cve="CVE-2024-A", severity="high"),
        Vulnerability(asset_id=a.id, cve="CVE-2024-B", severity="medium"),
    ])
    db.commit()

    r = client.get(f"/api/v1/assets/{a.id}/vulnerabilities", headers=auth_header)
    assert r.status_code == 200
    assert r.json()["total"] == 2


# ----- Filters / 422 validation --------------------------------------------

def test_vulnerabilities_filter_by_severity(client, auth_header, db):
    a = Asset(wazuh_agent_id="001", hostname="debian")
    db.add(a)
    db.commit()
    db.refresh(a)
    db.add_all([
        Vulnerability(asset_id=a.id, cve="CVE-A", severity="high"),
        Vulnerability(asset_id=a.id, cve="CVE-B", severity="low"),
    ])
    db.commit()

    r = client.get("/api/v1/vulnerabilities?severity=high", headers=auth_header)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["cve"] == "CVE-A"


def test_invalid_severity_filter_is_422(client, auth_header):
    r = client.get("/api/v1/vulnerabilities?severity=bogus", headers=auth_header)
    assert r.status_code == 422


def test_invalid_action_in_create_job_is_422(client, auth_header):
    r = client.post(
        "/api/v1/remediation/jobs",
        headers=auth_header,
        json={"asset_id": "x", "action": "launch_missiles"},
    )
    assert r.status_code == 422
    # Pydantic surfaces the valid vocabulary in the error body so frontends
    # can render a sensible dropdown without docs.
    assert "package_update" in r.text


# ----- OpenAPI is sane -----------------------------------------------------

def test_openapi_has_expected_paths(client):
    paths = set(client.get("/openapi.json").json()["paths"].keys())
    must_have = {
        "/health",
        "/api/v1/health",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/integrations/wazuh/health",
        "/api/v1/integrations/ansible/health",
        "/api/v1/sync/wazuh/agents",
        "/api/v1/sync/wazuh/vulnerabilities",
        "/api/v1/assets",
        "/api/v1/assets/{asset_id}",
        "/api/v1/vulnerabilities",
        "/api/v1/remediation/jobs",
        "/api/v1/remediation/jobs/{job_id}",
        "/api/v1/remediation/jobs/{job_id}/approve",
        "/api/v1/remediation/jobs/{job_id}/launch",
        "/api/v1/remediation/jobs/{job_id}/refresh",
        "/api/v1/remediation/jobs/{job_id}/verify",
        "/api/v1/audit-logs",
        "/api/v1/roles",
        "/api/v1/users",
        "/api/v1/users/{user_id}",
        "/api/v1/users/{user_id}/asset-scopes",
        "/api/v1/users/{user_id}/asset-scopes/{asset_id}",
        "/api/v1/dashboard/summary",
    }
    missing = must_have - paths
    assert not missing, f"missing OpenAPI paths: {missing}"
