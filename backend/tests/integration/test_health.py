"""Smoke test: /health risponde 200 e include status."""


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["database"] == "ok"


def test_status_alias(client):
    """/status e' alias di /health."""
    r = client.get("/status")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "NerdNostalgia" in r.json()["message"]
