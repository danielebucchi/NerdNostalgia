"""Registrazione cliente: consenso, aggancio ordini, accesso con email."""


def _register(client, email, **extra):
    body = {"email": email, "password": "unapasswordlunga"}
    body.update(extra)
    return client.post("/api/auth/register", json=body)


def test_register_returns_a_token(client):
    """Chi si registra ha appena scritto email e password: farglielo rifare
    per accedere e' un passaggio inutile."""
    r = _register(client, "nuovo@test.it", full_name="Nuovo Cliente")
    assert r.status_code == 201, r.text
    assert r.json()["access_token"]


def test_registered_user_logs_in_with_the_email(client):
    _register(client, "accesso@test.it")
    r = client.post(
        "/api/auth/login",
        data={"username": "accesso@test.it", "password": "unapasswordlunga"},
    )
    assert r.status_code == 200, r.text


def test_customer_gets_the_user_role(client, admin_headers):
    _register(client, "ruolo@test.it")
    r = client.post(
        "/api/auth/login",
        data={"username": "ruolo@test.it", "password": "unapasswordlunga"},
    )
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["role"] == "USER"


def test_duplicate_email_is_refused(client):
    _register(client, "doppio@test.it")
    r = _register(client, "doppio@test.it")
    assert r.status_code == 409
    assert "accedere" in r.json()["detail"].lower()


def test_marketing_consent_is_off_unless_asked(client, admin_headers):
    """Il consenso non si deduce dall'iscrizione: deve essere una scelta
    esplicita, altrimenti non e' valido."""
    _register(client, "senza@test.it")
    users = client.get("/api/users/", headers=admin_headers).json()
    u = next(x for x in users if x["email"] == "senza@test.it")
    assert u.get("marketing_consent") in (False, None, 0)


def test_short_password_is_refused(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "corta@test.it", "password": "breve"},
    )
    assert r.status_code == 422


def test_guest_orders_are_attached_on_registration(
    client, admin_headers, admin_user,
):
    """Chi ha comprato da ospite e poi si registra con la stessa email deve
    ritrovare l'ordine nello storico, non perderlo."""
    art = client.post(
        "/api/articles/", headers=admin_headers,
        json={
            "user_id": admin_user.id, "title": "Pezzo", "price": 9,
            "currency": "EUR", "condition": "USED", "status": "PUBLISHED",
            "quantity": 1,
        },
    ).json()
    ordine = client.post("/api/orders/", json={
        "buyer_name": "Ospite Prova", "buyer_email": "ospite@test.it",
        "inpost_point_id": "IT12345",
        "ship_street": "Via Grande 10", "ship_city": "Livorno",
        "ship_postal_code": "57123",
        "items": [{"article_id": art["id"], "quantity": 1}],
    }).json()

    r = _register(client, "ospite@test.it")
    assert r.status_code == 201, r.text

    detail = client.get(
        f"/api/orders/{ordine['id']}", headers=admin_headers
    ).json()
    assert detail["user_id"] is not None
