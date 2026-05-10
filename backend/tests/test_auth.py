"""Auth + RBAC + asset-scope + SoD tests.

Drives the JWT login surface and verifies that every gate behaves correctly
against the role/permission/scope model: missing token returns 401,
insufficient permission returns 403, and superusers bypass asset scope.
"""

from __future__ import annotations

import pytest

from app.core.security import create_access_token, hash_password
from app.models import Asset, RemediationJob, Role, User, user_asset_scope_table


# ============================================================================
# Login flow
# ============================================================================

def test_login_success(client, db):
    db.add(User(
        username="alice",
        email="alice@test",
        hashed_password=hash_password("s3cret!"),
        is_active=True,
        is_superuser=False,
    ))
    db.commit()

    r = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "s3cret!"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0


def test_login_with_email_works(client, db):
    db.add(User(
        username="alice",
        email="alice@test",
        hashed_password=hash_password("s3cret!"),
        is_active=True,
    ))
    db.commit()

    r = client.post(
        "/api/v1/auth/login",
        json={"username": "alice@test", "password": "s3cret!"},
    )
    assert r.status_code == 200


def test_login_wrong_password_is_401(client, db):
    db.add(User(
        username="alice",
        email="alice@test",
        hashed_password=hash_password("s3cret!"),
        is_active=True,
    ))
    db.commit()

    r = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "nope"},
    )
    assert r.status_code == 401


def test_login_unknown_user_is_401(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "ghost", "password": "whatever"},
    )
    assert r.status_code == 401


def test_inactive_user_cannot_log_in(client, db):
    db.add(User(
        username="alice",
        email="alice@test",
        hashed_password=hash_password("s3cret!"),
        is_active=False,  # disabled
    ))
    db.commit()

    r = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "s3cret!"},
    )
    assert r.status_code == 401


# ============================================================================
# Token validation on protected routes
# ============================================================================

def test_protected_without_token_is_401(client):
    r = client.get("/api/v1/assets")
    assert r.status_code == 401


def test_protected_with_garbage_token_is_401(client):
    r = client.get(
        "/api/v1/assets",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert r.status_code == 401


def test_protected_with_token_for_deleted_user_is_401(client, db, token_for):
    # Issue a valid JWT for a user that we then remove from the DB.
    token, user = token_for("ghost")
    db.delete(db.get(User, user.id))
    db.commit()

    r = client.get(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401


def test_protected_with_token_for_inactive_user_is_401(client, db, token_for):
    token, user = token_for("alice")
    obj = db.get(User, user.id)
    obj.is_active = False
    db.commit()

    r = client.get(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401


# ============================================================================
# /auth/me reflects roles + permissions
# ============================================================================

def test_me_returns_identity_and_permissions(client, token_for):
    token, user = token_for(
        "carol",
        role_names=("security_analyst",),
        is_superuser=False,
    )
    r = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["username"] == "carol"
    assert body["roles"][0]["name"] == "security_analyst"
    # Analyst gets read + sync + remediation:create but NOT remediation:approve.
    assert "remediation:create" in body["permissions"]
    assert "remediation:approve" not in body["permissions"]


# ============================================================================
# Permission gating: 403 when role lacks permission
# ============================================================================

def test_viewer_cannot_run_sync(client, token_for, fake_wazuh):
    """``viewer`` role has read perms only — sync:run is missing -> 403."""
    token, _ = token_for("vince", role_names=("viewer",), is_superuser=False)

    r = client.post(
        "/api/v1/sync/wazuh/agents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_analyst_cannot_approve(
    client, db, token_for, approver_header, fake_awx, fake_wazuh,
):
    """Analyst can create jobs but not approve them."""
    # Seed an asset.
    asset = Asset(wazuh_agent_id="001", hostname="debian", os_platform="debian", status="active")
    db.add(asset)
    db.commit()
    db.refresh(asset)

    # Analyst (carol) creates the job.
    token, _ = token_for(
        "carol",
        role_names=("security_analyst",),
        is_superuser=True,  # superuser only to bypass scope, not perms
    )
    job_id = client.post(
        "/api/v1/remediation/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={"asset_id": asset.id, "action": "package_update"},
    ).json()["id"]

    # Analyst tries to approve -> 403 (missing remediation:approve).
    r = client.post(
        f"/api/v1/remediation/jobs/{job_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert r.status_code == 403


# ============================================================================
# Separation of Duties: creator cannot approve own job
# ============================================================================

def test_creator_cannot_approve_own_job(client, db, token_for):
    """Even with full perms, the creator's token cannot approve their own job."""
    asset = Asset(wazuh_agent_id="001", hostname="debian", os_platform="debian", status="active")
    db.add(asset)
    db.commit()
    db.refresh(asset)

    # Single user with both create and approve permissions (admin).
    token, _ = token_for("alice", role_names=("admin",), is_superuser=True)
    headers = {"Authorization": f"Bearer {token}"}

    job_id = client.post(
        "/api/v1/remediation/jobs",
        headers=headers,
        json={"asset_id": asset.id, "action": "package_update"},
    ).json()["id"]

    r = client.post(
        f"/api/v1/remediation/jobs/{job_id}/approve",
        headers=headers,
        json={},
    )
    assert r.status_code == 403
    assert "separation of duties" in r.text.lower()


# ============================================================================
# Asset scope: non-superuser sees only assets they have rows for
# ============================================================================

@pytest.fixture
def two_assets(db):
    a = Asset(wazuh_agent_id="001", hostname="alpha", status="active")
    b = Asset(wazuh_agent_id="002", hostname="beta",  status="active")
    db.add_all([a, b])
    db.commit()
    db.refresh(a)
    db.refresh(b)
    return a, b


def test_scoped_user_sees_only_assigned_assets(
    client, db, token_for, two_assets,
):
    a, _b = two_assets
    token, user = token_for(
        "scoped",
        role_names=("viewer",),
        is_superuser=False,
    )
    # Grant access only to asset ``a``.
    db.execute(
        user_asset_scope_table.insert().values(user_id=user.id, asset_id=a.id)
    )
    db.commit()

    r = client.get(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["hostname"] == "alpha"


def test_scoped_user_cannot_open_unscoped_asset_detail(
    client, db, token_for, two_assets,
):
    a, b = two_assets
    token, user = token_for(
        "scoped",
        role_names=("viewer",),
        is_superuser=False,
    )
    db.execute(
        user_asset_scope_table.insert().values(user_id=user.id, asset_id=a.id)
    )
    db.commit()

    headers = {"Authorization": f"Bearer {token}"}
    # Allowed asset.
    assert client.get(f"/api/v1/assets/{a.id}", headers=headers).status_code == 200
    # Forbidden asset.
    r = client.get(f"/api/v1/assets/{b.id}", headers=headers)
    assert r.status_code == 403


def test_superuser_sees_all_assets_regardless_of_scope(
    client, db, token_for, two_assets,
):
    token, _ = token_for(
        "root",
        role_names=("admin",),
        is_superuser=True,
    )
    r = client.get(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["total"] == 2


def test_user_with_no_scope_sees_no_assets(
    client, token_for, two_assets,
):
    """Default for non-superusers without explicit scope rows: empty result."""
    token, _ = token_for(
        "noscope",
        role_names=("viewer",),
        is_superuser=False,
    )
    r = client.get(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["total"] == 0


# ============================================================================
# Login emits an audit row
# ============================================================================

def test_login_writes_audit_row(client, db):
    db.add(User(
        username="alice",
        email="alice@test",
        hashed_password=hash_password("s3cret!"),
        is_active=True,
    ))
    db.commit()

    client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "s3cret!"},
    )

    from app.models import AuditLog
    actions = {a.action for a in db.query(AuditLog).all()}
    assert "auth.login.success" in actions


def test_failed_login_writes_audit_row(client, db):
    client.post(
        "/api/v1/auth/login",
        json={"username": "ghost", "password": "nope"},
    )

    from app.models import AuditLog
    actions = {a.action for a in db.query(AuditLog).all()}
    assert "auth.login.failed" in actions
