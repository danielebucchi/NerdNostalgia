"""Users API: admin-only su tutti gli endpoint (regression test del fix).

Storia: prima POST /api/users/ era pubblico e accettava role=ADMIN, chiunque
poteva creare admin via API. Ora richiede require_admin come gli altri verbi.
"""


def _user_payload(**override):
    base = {
        "username": "newuser",
        "email": "new@user.io",
        "password": "secret123",
        "full_name": "New User",
        "role": "USER",
    }
    base.update(override)
    return base


def test_create_user_unauthenticated_rejected(client):
    """POST anonimo deve rispondere 401 (era 201 prima del fix)."""
    r = client.post("/api/users/", json=_user_payload())
    assert r.status_code == 401, (
        "POST /api/users/ deve essere admin-only. "
        f"got {r.status_code}: {r.text}"
    )


def test_create_admin_via_api_blocked_without_token(client):
    """Anche se passano role=ADMIN, senza token niente."""
    r = client.post("/api/users/", json=_user_payload(role="ADMIN"))
    assert r.status_code == 401


def test_admin_can_create_user(client, admin_headers, admin_user):
    r = client.post(
        "/api/users/", headers=admin_headers, json=_user_payload(),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["username"] == "newuser"
    assert body["role"] == "USER"


def test_admin_can_create_another_admin(client, admin_headers, admin_user):
    r = client.post(
        "/api/users/", headers=admin_headers,
        json=_user_payload(username="admin2", email="a2@test.io", role="ADMIN"),
    )
    assert r.status_code == 201
    assert r.json()["role"] == "ADMIN"


def test_list_users_admin_only(client):
    r = client.get("/api/users/")
    assert r.status_code == 401


def test_admin_can_list_users(client, admin_headers, admin_user):
    r = client.get("/api/users/", headers=admin_headers)
    assert r.status_code == 200
    items = r.json()
    assert any(u["username"] == "admin" for u in items)
