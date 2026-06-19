"""Test su POST /api/inquiries/: submit, honeypot, rate limit."""
import pytest


def _payload(**override):
    base = {
        "name": "Mario Rossi",
        "email": "mario@example.com",
        "message": "Vorrei sapere se l'articolo e' ancora disponibile",
    }
    base.update(override)
    return base


def test_submit_inquiry_success(client):
    r = client.post("/api/inquiries/", json=_payload())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Mario Rossi"
    assert body["email"] == "mario@example.com"
    assert body["status"] == "NEW"
    assert body["id"] > 0


def test_submit_validates_email(client):
    r = client.post("/api/inquiries/", json=_payload(email="non-una-email"))
    assert r.status_code == 422


def test_submit_message_too_short(client):
    r = client.post("/api/inquiries/", json=_payload(message="ciao"))
    assert r.status_code == 422


def test_honeypot_field_rejects_silently(client, db_session):
    """Un bot riempe 'website' → la risposta sembra successo (id=0) ma nessun
    record in DB."""
    from models.db import Inquiry

    before = db_session.query(Inquiry).count()
    r = client.post(
        "/api/inquiries/",
        json=_payload(website="https://spammer.example"),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == 0  # marker honeypot
    after = db_session.query(Inquiry).count()
    assert after == before, "Honeypot non deve creare record"


def test_rate_limit_blocks_6th_request_per_minute(client):
    """slowapi: 5/min. Il sesto deve essere 429."""
    for i in range(5):
        r = client.post("/api/inquiries/", json=_payload(message=f"test msg {i}"))
        assert r.status_code == 201, f"#{i}: {r.text}"
    r = client.post("/api/inquiries/", json=_payload(message="should be blocked"))
    assert r.status_code == 429


def test_submit_to_unknown_article_400(client):
    r = client.post(
        "/api/inquiries/",
        json=_payload(article_id=99999),
    )
    assert r.status_code == 400
