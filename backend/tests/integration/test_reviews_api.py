"""Recensioni: si scrive solo da un ordine completato, e pubblica l'admin."""
import pytest


@pytest.fixture()
def ordine_completato(client, admin_headers, admin_user):
    """Ordine portato fino a COMPLETATO: l'unico stato da cui si recensisce."""
    art = client.post(
        "/api/articles/", headers=admin_headers,
        json={
            "user_id": admin_user.id, "title": "Pezzo recensibile", "price": 14,
            "currency": "EUR", "condition": "USED", "status": "PUBLISHED",
            "quantity": 1,
        },
    ).json()
    o = client.post("/api/orders/", json={
        "buyer_name": "Giulia Bianchi", "buyer_email": "giulia@test.it",
        "inpost_point_id": "IT12345",
        "ship_street": "Via Grande 10", "ship_city": "Livorno",
        "ship_postal_code": "57123",
        "items": [{"article_id": art["id"], "quantity": 1}],
    }).json()
    for payload in (
        {"status": "PAID"},
        {"status": "SHIPPED", "tracking_code": "XX1"},
        {"status": "COMPLETED"},
    ):
        client.patch(f"/api/orders/{o['id']}", headers=admin_headers, json=payload)
    return o


def _scrivi(client, order, **extra):
    body = {
        "order_id": order["id"], "token": order["public_token"], "rating": 5,
    }
    body.update(extra)
    return client.post("/api/reviews/", json=body)


def test_cannot_review_before_completion(client, admin_headers, admin_user):
    """Il completamento e' la prova che la transazione e' finita: prima non
    c'e' ancora niente da raccontare."""
    art = client.post(
        "/api/articles/", headers=admin_headers,
        json={
            "user_id": admin_user.id, "title": "Non finito", "price": 10,
            "currency": "EUR", "condition": "USED", "status": "PUBLISHED",
            "quantity": 1,
        },
    ).json()
    o = client.post("/api/orders/", json={
        "buyer_name": "Tizio Test", "buyer_email": "t@test.it",
        "inpost_point_id": "IT1", "ship_street": "Via Grande 10",
        "ship_city": "Livorno", "ship_postal_code": "57123",
        "items": [{"article_id": art["id"], "quantity": 1}],
    }).json()

    r = _scrivi(client, o)
    assert r.status_code == 400
    assert "completato" in r.json()["detail"].lower()


def test_wrong_token_looks_like_a_missing_order(client, ordine_completato):
    """404 e non 403: gli id non devono essere enumerabili per scoprire chi
    ha comprato cosa."""
    r = client.post("/api/reviews/", json={
        "order_id": ordine_completato["id"], "token": "z" * 32, "rating": 5,
    })
    assert r.status_code == 404


def test_review_starts_hidden(client, ordine_completato):
    """Niente va online senza che l'abbia letto l'admin."""
    r = _scrivi(client, ordine_completato, body="Imballo curatissimo.")
    assert r.status_code == 201, r.text
    assert client.get("/api/reviews/").json() == []
    assert client.get("/api/reviews/summary").json()["count"] == 0


def test_one_review_per_order(client, ordine_completato):
    _scrivi(client, ordine_completato)
    r = _scrivi(client, ordine_completato, rating=1)
    assert r.status_code == 409


def test_rating_must_be_between_one_and_five(client, ordine_completato):
    assert _scrivi(client, ordine_completato, rating=0).status_code == 422
    assert _scrivi(client, ordine_completato, rating=6).status_code == 422


def test_approving_publishes_it(client, admin_headers, ordine_completato):
    _scrivi(client, ordine_completato, body="Tutto perfetto.")
    pending = client.get(
        "/api/reviews/admin?status=PENDING", headers=admin_headers
    ).json()
    assert len(pending) == 1

    client.patch(
        f"/api/reviews/{pending[0]['id']}", headers=admin_headers,
        json={"status": "APPROVED", "reply": "Grazie!"},
    )

    pubbliche = client.get("/api/reviews/").json()
    assert len(pubbliche) == 1
    assert pubbliche[0]["reply"] == "Grazie!"
    assert pubbliche[0]["author_name"] == "Giulia Bianchi"
    # Il pubblico non deve vedere a quale ordine si riferisce
    assert "order_id" not in pubbliche[0]
    assert client.get("/api/reviews/summary").json() == {"count": 1, "average": 5.0}


def test_rejecting_keeps_it_hidden(client, admin_headers, ordine_completato):
    _scrivi(client, ordine_completato)
    rid = client.get("/api/reviews/admin", headers=admin_headers).json()[0]["id"]
    client.patch(
        f"/api/reviews/{rid}", headers=admin_headers, json={"status": "REJECTED"}
    )
    assert client.get("/api/reviews/").json() == []


def test_moderation_requires_admin(client, ordine_completato):
    _scrivi(client, ordine_completato)
    assert client.get("/api/reviews/admin").status_code == 401
    assert client.patch("/api/reviews/1", json={"status": "APPROVED"}).status_code == 401


def test_can_review_tells_the_page_what_to_show(client, ordine_completato):
    url = (
        f"/api/reviews/can-review?order_id={ordine_completato['id']}"
        f"&token={ordine_completato['public_token']}"
    )
    assert client.get(url).json()["already_reviewed"] is False
    _scrivi(client, ordine_completato)
    assert client.get(url).json()["already_reviewed"] is True
