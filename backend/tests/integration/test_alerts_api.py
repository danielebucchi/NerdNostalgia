"""Category alerts: subscribe, honeypot, unsubscribe, notifica su publish."""
import pytest

from models.db import Category
from utils.category_alerts import unsubscribe_token


@pytest.fixture()
def category_id(db_session):
    cat = Category(name="Giochi test", slug="giochi-test")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat.id


def test_subscribe_all_categories(client):
    r = client.post("/api/alerts/", json={"email": "fan@test.it"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "fan@test.it"
    assert body["category_id"] is None


def test_subscribe_specific_category(client, category_id):
    r = client.post(
        "/api/alerts/", json={"email": "fan@test.it", "category_id": category_id},
    )
    assert r.status_code == 201
    assert r.json()["category_id"] == category_id


def test_subscribe_unknown_category_400(client):
    r = client.post("/api/alerts/", json={"email": "fan@test.it", "category_id": 9999})
    assert r.status_code == 400


def test_subscribe_idempotent(client, category_id):
    a = client.post(
        "/api/alerts/", json={"email": "Fan@Test.it", "category_id": category_id},
    ).json()
    b = client.post(
        "/api/alerts/", json={"email": "fan@test.it", "category_id": category_id},
    ).json()
    assert a["id"] == b["id"]


def test_honeypot_fake_success(client, admin_headers):
    r = client.post(
        "/api/alerts/", json={"email": "bot@spam.io", "website": "https://spam"},
    )
    assert r.status_code == 201
    assert r.json()["id"] == 0
    # Ma non e' stato salvato niente
    subs = client.get("/api/alerts/", headers=admin_headers).json()
    assert all(s["email"] != "bot@spam.io" for s in subs)


def test_unsubscribe_with_valid_token(client, admin_headers, category_id):
    client.post("/api/alerts/", json={"email": "fan@test.it"})
    client.post("/api/alerts/", json={"email": "fan@test.it", "category_id": category_id})

    token = unsubscribe_token("fan@test.it")
    r = client.get(f"/api/alerts/unsubscribe?email=fan@test.it&token={token}")
    assert r.status_code == 200
    assert "Disiscrizione completata" in r.text

    subs = client.get("/api/alerts/", headers=admin_headers).json()
    assert subs == []


def test_unsubscribe_bad_token_403(client):
    client.post("/api/alerts/", json={"email": "fan@test.it"})
    r = client.get("/api/alerts/unsubscribe?email=fan@test.it&token=nope")
    assert r.status_code == 403


def test_publish_triggers_notification(client, admin_headers, admin_user, category_id, monkeypatch):
    """La transizione DRAFT → PUBLISHED manda l'avviso agli iscritti giusti."""
    sent: list = []

    def fake_send_email(*, to, subject, text_body, html_body=None, reply_to=None):
        sent.append((to, subject))
        return True

    import utils.category_alerts as ca
    monkeypatch.setattr(ca, "send_email", fake_send_email)

    # Iscritti: uno alla categoria giusta, uno a tutte, uno a un'altra
    other_cat = client.post  # noqa: F841  (leggibilita')
    client.post("/api/alerts/", json={"email": "cat@test.it", "category_id": category_id})
    client.post("/api/alerts/", json={"email": "all@test.it"})

    art = client.post(
        "/api/articles/",
        headers=admin_headers,
        json={
            "user_id": admin_user.id,
            "title": "SNES Mini",
            "price": 60,
            "currency": "EUR",
            "condition": "USED",
            "status": "DRAFT",
            "quantity": 1,
            "category_id": category_id,
        },
    ).json()

    r = client.post(f"/api/articles/{art['id']}/publish", headers=admin_headers)
    assert r.status_code == 200

    recipients = sorted(to for to, _ in sent)
    assert recipients == ["all@test.it", "cat@test.it"]
    assert all("SNES Mini" in subj for _, subj in sent)

    # Ri-pubblicare un articolo gia' PUBLISHED non rimanda le email
    sent.clear()
    client.post(f"/api/articles/{art['id']}/publish", headers=admin_headers)
    assert sent == []


def test_orders_cap_prefixes_from_settings(client, admin_headers, admin_user):
    """Cambiare hand_exchange_cap_prefixes dalle settings cambia la validazione."""
    art = client.post(
        "/api/articles/",
        headers=admin_headers,
        json={
            "user_id": admin_user.id,
            "title": "Gioco", "price": 10, "currency": "EUR",
            "condition": "USED", "status": "PUBLISHED", "quantity": 1,
        },
    ).json()

    def order_payload(cap):
        return {
            "buyer_name": "Mario", "buyer_email": "mario@test.it",
            "ship_street": "Via Roma 1", "ship_city": "Lucca",
            "ship_postal_code": cap, "hand_exchange": True,
            "items": [{"article_id": art["id"], "quantity": 1}],
        }

    # CAP 55xxx (Lucca) non abilitato di default
    r = client.post("/api/orders/", json=order_payload("55100"))
    assert r.status_code == 400

    # Abilito il prefisso 55 dalle settings
    client.put(
        "/api/settings/",
        headers=admin_headers,
        json={"values": {"hand_exchange_cap_prefixes": "55,56,57"}},
    )
    r = client.post("/api/orders/", json=order_payload("55100"))
    assert r.status_code == 201, r.text
    assert float(r.json()["shipping_total"]) == 0.0
