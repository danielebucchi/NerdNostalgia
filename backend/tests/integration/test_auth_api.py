"""Login, /me, e guard require_admin."""


def test_login_success(client, admin_user):
    r = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0


def test_login_wrong_password(client, admin_user):
    r = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "sbagliata"},
    )
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post(
        "/api/auth/login",
        data={"username": "ghost", "password": "x"},
    )
    assert r.status_code == 401


def test_me_with_token(client, admin_headers, admin_user):
    r = client.get("/api/auth/me", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "admin"
    assert body["role"] == "ADMIN"


def test_me_without_token(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_invalid_token(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert r.status_code == 401


def test_admin_only_endpoint_requires_auth(client):
    """Inquiries listing e' admin-only."""
    r = client.get("/api/inquiries/")
    assert r.status_code == 401


def test_admin_endpoint_with_admin_token(client, admin_headers, admin_user):
    """L'admin puo' accedere a /api/inquiries/."""
    r = client.get("/api/inquiries/", headers=admin_headers)
    assert r.status_code == 200
    assert "items" in r.json()
