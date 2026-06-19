"""Platforms CRUD."""


def test_list_platforms_empty(client, admin_headers):
    r = client.get("/api/platforms/", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_create_platform(client, admin_headers):
    r = client.post(
        "/api/platforms/",
        headers=admin_headers,
        json={"name": "TestStore", "slug": "teststore", "icon": "🧪", "display_order": 15},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "TestStore"
    assert body["slug"] == "teststore"
    assert body["is_active"] is True


def test_create_duplicate_slug_fails(client, admin_headers):
    payload = {"name": "X", "slug": "dup", "display_order": 10}
    r1 = client.post("/api/platforms/", headers=admin_headers, json=payload)
    assert r1.status_code == 201
    r2 = client.post("/api/platforms/", headers=admin_headers, json=payload)
    # SQLite UNIQUE constraint -> 400/409 a seconda del wrapping
    assert r2.status_code in (400, 409, 500)


def test_update_platform(client, admin_headers):
    created = client.post(
        "/api/platforms/",
        headers=admin_headers,
        json={"name": "Old", "slug": "old", "display_order": 10},
    ).json()
    r = client.patch(
        f"/api/platforms/{created['id']}",
        headers=admin_headers,
        json={"name": "New", "is_active": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "New"
    assert body["is_active"] is False


def test_delete_platform(client, admin_headers):
    created = client.post(
        "/api/platforms/",
        headers=admin_headers,
        json={"name": "Z", "slug": "z", "display_order": 99},
    ).json()
    r = client.delete(f"/api/platforms/{created['id']}", headers=admin_headers)
    assert r.status_code == 204


def test_platforms_admin_required(client):
    r = client.post(
        "/api/platforms/",
        json={"name": "x", "slug": "x", "display_order": 1},
    )
    assert r.status_code == 401
