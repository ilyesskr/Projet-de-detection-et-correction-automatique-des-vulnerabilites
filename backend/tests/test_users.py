"""User CRUD + asset-scope management tests.

Drives the admin-only ``/users`` and ``/roles`` endpoints. ``auth_header``
is a superuser admin (alice); ``token_for`` builds a different user / role
combination when we need to test permission gating.
"""

from __future__ import annotations

import pytest

from app.core.security import hash_password
from app.models import Asset, AuditLog, Role, User, user_asset_scope_table


# ============================================================================
# /roles list
# ============================================================================

def test_roles_list_returns_seeded_roles(client, auth_header, db):
    # ``auth_header`` already created the ``admin`` role via its underlying
    # user fixture — only add the ones it didn't.
    db.add_all([
        Role(name="viewer"),
        Role(name="security_analyst"),
    ])
    db.commit()

    r = client.get("/api/v1/roles", headers=auth_header)
    assert r.status_code == 200
    names = [item["name"] for item in r.json()]
    assert names == sorted(names)
    assert {"admin", "viewer", "security_analyst"}.issubset(set(names))


def test_roles_list_requires_users_manage(client, token_for):
    """A viewer (no users:manage) cannot read the role catalog."""
    token, _ = token_for("vince", role_names=("viewer",), is_superuser=False)
    r = client.get("/api/v1/roles", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


# ============================================================================
# Create
# ============================================================================

def test_create_user_returns_201_and_writes_audit(client, auth_header, db):
    db.add(Role(name="viewer"))
    db.commit()

    r = client.post(
        "/api/v1/users",
        headers=auth_header,
        json={
            "username":    "carol",
            "email":       "carol@example.com",
            "password":    "carolPass123",
            "is_active":   True,
            "is_superuser": False,
            "role_names":  ["viewer"],
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["username"] == "carol"
    assert "hashed_password" not in body
    assert [r["name"] for r in body["roles"]] == ["viewer"]

    # Audit row recorded under the actor's username (alice).
    actions = {a.action for a in db.query(AuditLog).all()}
    assert "user.created" in actions


def test_create_user_username_collision_is_409(client, auth_header, db):
    db.add(User(
        username="carol", email="carol@example.com",
        hashed_password=hash_password("x"), is_active=True,
    ))
    db.commit()

    r = client.post(
        "/api/v1/users",
        headers=auth_header,
        json={
            "username": "carol",
            "email":    "different@example.com",
            "password": "anyPass123",
        },
    )
    assert r.status_code == 409


def test_create_user_email_collision_is_409(client, auth_header, db):
    db.add(User(
        username="carol", email="carol@example.com",
        hashed_password=hash_password("x"), is_active=True,
    ))
    db.commit()

    r = client.post(
        "/api/v1/users",
        headers=auth_header,
        json={
            "username": "different",
            "email":    "carol@example.com",
            "password": "anyPass123",
        },
    )
    assert r.status_code == 409


def test_create_user_unknown_role_is_400(client, auth_header):
    r = client.post(
        "/api/v1/users",
        headers=auth_header,
        json={
            "username":   "dan",
            "email":      "dan@example.com",
            "password":   "danPass123",
            "role_names": ["does_not_exist"],
        },
    )
    assert r.status_code == 400
    assert "unknown role" in r.text.lower()


def test_create_requires_users_manage(client, token_for):
    token, _ = token_for("vince", role_names=("viewer",), is_superuser=False)
    r = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "x", "email": "x@y.z", "password": "anyPass123"},
    )
    assert r.status_code == 403


# ============================================================================
# List / Get
# ============================================================================

def test_list_users_paginates(client, auth_header, db):
    for i in range(3):
        db.add(User(
            username=f"u{i}", email=f"u{i}@example.com",
            hashed_password=hash_password("x"), is_active=True,
        ))
    db.commit()

    r = client.get("/api/v1/users", headers=auth_header)
    assert r.status_code == 200
    body = r.json()
    # alice (the auth_header user) is also in the DB -> total = 3 + 1.
    assert body["total"] == 4
    assert body["limit"] == 50


def test_list_users_filter_inactive(client, auth_header, db):
    db.add_all([
        User(username="active",   email="a@example.org", hashed_password=hash_password("x"), is_active=True),
        User(username="inactive", email="i@example.org", hashed_password=hash_password("x"), is_active=False),
    ])
    db.commit()

    r = client.get("/api/v1/users?is_active=false", headers=auth_header)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["username"] == "inactive"


def test_get_user_404(client, auth_header):
    r = client.get("/api/v1/users/no-such-id", headers=auth_header)
    assert r.status_code == 404


# ============================================================================
# Update (PATCH)
# ============================================================================

def test_patch_user_changes_role_set(client, auth_header, db):
    db.add_all([Role(name="viewer"), Role(name="security_analyst")])
    user = User(
        username="dave", email="dave@example.org",
        hashed_password=hash_password("x"), is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    r = client.patch(
        f"/api/v1/users/{user.id}",
        headers=auth_header,
        json={"role_names": ["security_analyst"]},
    )
    assert r.status_code == 200
    assert [r["name"] for r in r.json()["roles"]] == ["security_analyst"]


def test_patch_user_password_change_lets_them_log_in(client, auth_header, db):
    user = User(
        username="erin", email="erin@example.org",
        hashed_password=hash_password("oldPass123"), is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Old password works.
    r1 = client.post("/api/v1/auth/login", json={"username": "erin", "password": "oldPass123"})
    assert r1.status_code == 200

    # Admin rotates erin's password.
    r2 = client.patch(
        f"/api/v1/users/{user.id}",
        headers=auth_header,
        json={"password": "newPass123"},
    )
    assert r2.status_code == 200

    # Old fails, new works.
    assert client.post("/api/v1/auth/login", json={"username": "erin", "password": "oldPass123"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"username": "erin", "password": "newPass123"}).status_code == 200


def test_patch_user_email_collision_is_409(client, auth_header, db):
    db.add_all([
        User(username="frank",  email="frank@example.org",  hashed_password=hash_password("x"), is_active=True),
        User(username="george", email="george@example.org", hashed_password=hash_password("x"), is_active=True),
    ])
    db.commit()
    george = db.query(User).filter_by(username="george").one()

    r = client.patch(
        f"/api/v1/users/{george.id}",
        headers=auth_header,
        json={"email": "frank@example.org"},
    )
    assert r.status_code == 409


def test_patch_unknown_user_is_404(client, auth_header):
    r = client.patch(
        "/api/v1/users/no-such-id",
        headers=auth_header,
        json={"is_active": False},
    )
    assert r.status_code == 404


# ============================================================================
# Delete
# ============================================================================

def test_delete_user_returns_204(client, auth_header, db):
    user = User(
        username="hank", email="hank@example.org",
        hashed_password=hash_password("x"), is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id  # capture before delete; the ORM object becomes stale.

    r = client.delete(f"/api/v1/users/{user_id}", headers=auth_header)
    assert r.status_code == 204

    # The route's get_db session committed the delete; this fixture's session
    # may still have the row in its identity map. Expire and look up by id.
    db.expire_all()
    assert db.get(User, user_id) is None


def test_delete_self_is_blocked(client, auth_header, db):
    """alice (the auth_header user) cannot delete herself."""
    alice = db.query(User).filter_by(username="alice").one()
    r = client.delete(f"/api/v1/users/{alice.id}", headers=auth_header)
    assert r.status_code == 400
    assert "logged in" in r.text.lower()


# ============================================================================
# Asset scope
# ============================================================================

@pytest.fixture
def scoped_user_and_asset(db):
    user = User(
        username="ivan", email="ivan@example.org",
        hashed_password=hash_password("x"), is_active=True, is_superuser=False,
    )
    asset = Asset(wazuh_agent_id="001", hostname="alpha", status="active")
    db.add_all([user, asset])
    db.commit()
    db.refresh(user)
    db.refresh(asset)
    return user, asset


def test_grant_asset_scope_204_and_visible(
    client, auth_header, db, scoped_user_and_asset,
):
    user, asset = scoped_user_and_asset

    r = client.post(
        f"/api/v1/users/{user.id}/asset-scopes",
        headers=auth_header,
        json={"asset_id": asset.id},
    )
    assert r.status_code == 204

    r2 = client.get(
        f"/api/v1/users/{user.id}/asset-scopes",
        headers=auth_header,
    )
    assert r2.status_code == 200
    assert [a["id"] for a in r2.json()] == [asset.id]


def test_grant_asset_scope_is_idempotent(
    client, auth_header, scoped_user_and_asset,
):
    user, asset = scoped_user_and_asset
    headers = auth_header
    body = {"asset_id": asset.id}

    assert client.post(f"/api/v1/users/{user.id}/asset-scopes", headers=headers, json=body).status_code == 204
    # Re-grant — must not error.
    assert client.post(f"/api/v1/users/{user.id}/asset-scopes", headers=headers, json=body).status_code == 204

    # Still exactly one row.
    r = client.get(f"/api/v1/users/{user.id}/asset-scopes", headers=headers)
    assert len(r.json()) == 1


def test_revoke_asset_scope_204(client, auth_header, db, scoped_user_and_asset):
    user, asset = scoped_user_and_asset
    db.execute(
        user_asset_scope_table.insert().values(user_id=user.id, asset_id=asset.id)
    )
    db.commit()

    r = client.delete(
        f"/api/v1/users/{user.id}/asset-scopes/{asset.id}",
        headers=auth_header,
    )
    assert r.status_code == 204

    r2 = client.get(f"/api/v1/users/{user.id}/asset-scopes", headers=auth_header)
    assert r2.json() == []


def test_grant_unknown_user_is_404(client, auth_header, scoped_user_and_asset):
    _, asset = scoped_user_and_asset
    r = client.post(
        "/api/v1/users/ghost/asset-scopes",
        headers=auth_header,
        json={"asset_id": asset.id},
    )
    assert r.status_code == 404


def test_grant_unknown_asset_is_404(client, auth_header, scoped_user_and_asset):
    user, _ = scoped_user_and_asset
    r = client.post(
        f"/api/v1/users/{user.id}/asset-scopes",
        headers=auth_header,
        json={"asset_id": "ghost"},
    )
    assert r.status_code == 404


# ============================================================================
# End-to-end: create -> grant scope -> login -> see only that asset
# ============================================================================

def test_admin_can_provision_a_scoped_user_who_then_sees_only_that_asset(
    client, auth_header, db,
):
    """The full admin onboarding flow exercised through the API surface."""
    db.add(Role(name="viewer"))
    a1 = Asset(wazuh_agent_id="001", hostname="alpha")
    a2 = Asset(wazuh_agent_id="002", hostname="beta")
    db.add_all([a1, a2])
    db.commit()
    db.refresh(a1)

    # 1. Admin creates a viewer.
    new_user = client.post(
        "/api/v1/users",
        headers=auth_header,
        json={
            "username":   "newbie",
            "email":      "newbie@example.org",
            "password":   "newPass1234",
            "role_names": ["viewer"],
        },
    ).json()

    # 2. Admin grants scope on asset alpha only.
    r = client.post(
        f"/api/v1/users/{new_user['id']}/asset-scopes",
        headers=auth_header,
        json={"asset_id": a1.id},
    )
    assert r.status_code == 204

    # 3. Newbie logs in.
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "newbie", "password": "newPass1234"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # 4. Newbie sees only alpha.
    listing = client.get("/api/v1/assets", headers=headers).json()
    assert listing["total"] == 1
    assert listing["items"][0]["hostname"] == "alpha"
