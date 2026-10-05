"""Cancellazione dell'account chiesta dal cliente.

Se ne vanno profilo, indirizzi, iscrizione agli avvisi e recensioni.
Restano gli ORDINI: per le scritture contabili la legge impone dieci anni
(art. 2220 c.c.), quindi conservarle non e' una nostra scelta.
"""
from models.db import CategoryAlert, Order, Review, ReviewStatus, User

PWD = "unapasswordlunga"


def _db():
    from main import app
    from utils.session import get_db

    return next(app.dependency_overrides[get_db]())


def _register(client, email):
    return client.post(
        "/api/auth/register", json={"email": email, "password": PWD}
    )


def _headers(client, email):
    r = client.post("/api/auth/login", data={"username": email, "password": PWD})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _cliente(client, email):
    _register(client, email)
    return _headers(client, email)


# --- il caso base ---------------------------------------------------------


def test_the_account_is_gone(client):
    h = _cliente(client, "addio@test.it")

    r = client.request("DELETE", "/api/auth/me", json={"password": PWD}, headers=h)

    assert r.status_code == 200, r.text
    db = _db()
    try:
        assert db.query(User).filter(User.email == "addio@test.it").first() is None
    finally:
        db.close()


def test_the_old_password_no_longer_logs_in(client):
    h = _cliente(client, "sparito@test.it")
    client.request("DELETE", "/api/auth/me", json={"password": PWD}, headers=h)

    r = client.post("/api/auth/login", data={"username": "sparito@test.it", "password": PWD})

    assert r.status_code == 401


def test_the_saved_addresses_go_with_it(client):
    h = _cliente(client, "indirizzi@test.it")
    client.post(
        "/api/addresses",
        json={
            "full_name": "Mario Rossi",
            "street": "Via Roma 1",
            "city": "Pisa",
            "postal_code": "56100",
            "country": "Italia",
        },
        headers=h,
    )

    client.request("DELETE", "/api/auth/me", json={"password": PWD}, headers=h)

    db = _db()
    try:
        from models.db import ShippingAddress

        assert db.query(ShippingAddress).count() == 0
    finally:
        db.close()


def test_the_newsletter_subscription_goes_with_it(client):
    """Gli avvisi sono legati all'email e non all'utente: senza toglierli
    a mano continuerebbero ad arrivare a un account che non esiste piu'."""
    h = _cliente(client, "avvisi@test.it")
    db = _db()
    try:
        db.add(CategoryAlert(email="avvisi@test.it", category_id=None))
        db.commit()
    finally:
        db.close()

    client.request("DELETE", "/api/auth/me", json={"password": PWD}, headers=h)

    db = _db()
    try:
        assert (
            db.query(CategoryAlert)
            .filter(CategoryAlert.email == "avvisi@test.it")
            .count()
            == 0
        )
    finally:
        db.close()


def test_the_published_reviews_go_with_it(client):
    """Il vincolo stacca solo il collegamento, ma dentro la recensione
    resta scritto il nome dell'autore — ed e' pubblicato sul sito."""
    h = _cliente(client, "recensore@test.it")
    db = _db()
    try:
        uid = db.query(User).filter(User.email == "recensore@test.it").first().id
        # La recensione ha bisogno di un ordine vero: il vincolo lo esige,
        # ed e' lo stesso vincolo che garantisce che si recensisca solo
        # dopo aver comprato.
        ordine = Order(
            user_id=uid,
            buyer_name="Mario Rossi",
            buyer_email="recensore@test.it",
            ship_street="Via Roma 1",
            ship_city="Pisa",
            ship_postal_code="56100",
            ship_country="Italia",
            subtotal=10,
            shipping_total=0,
            grand_total=10,
            currency="EUR",
            public_token="tok-recensione",
        )
        db.add(ordine)
        db.flush()
        db.add(
            Review(
                order_id=ordine.id,
                user_id=uid,
                author_name="Mario Rossi",
                rating=5,
                body="Tutto benissimo",
                status=ReviewStatus.APPROVED,
            )
        )
        db.commit()
    finally:
        db.close()

    client.request("DELETE", "/api/auth/me", json={"password": PWD}, headers=h)

    db = _db()
    try:
        assert db.query(Review).filter(Review.author_name == "Mario Rossi").count() == 0
    finally:
        db.close()


# --- quello che la legge impone di tenere ---------------------------------


def test_the_orders_survive_the_account(client):
    """Dieci anni per le scritture contabili: non e' una nostra scelta."""
    h = _cliente(client, "ordini@test.it")
    db = _db()
    try:
        u = db.query(User).filter(User.email == "ordini@test.it").first()
        db.add(
            Order(
                user_id=u.id,
                buyer_name="Mario Rossi",
                buyer_email="ordini@test.it",
                ship_street="Via Roma 1",
                ship_city="Pisa",
                ship_postal_code="56100",
                ship_country="Italia",
                subtotal=10,
                shipping_total=0,
                grand_total=10,
                currency="EUR",
                public_token="tok-ordini",
            )
        )
        db.commit()
    finally:
        db.close()

    client.request("DELETE", "/api/auth/me", json={"password": PWD}, headers=h)

    db = _db()
    try:
        o = db.query(Order).filter(Order.public_token == "tok-ordini").first()
        assert o is not None
        # staccato dal profilo, ma conservato
        assert o.user_id is None
    finally:
        db.close()


# --- chi puo' chiederlo ---------------------------------------------------


def test_the_wrong_password_does_not_delete_anything(client):
    """E' l'unica prova che a chiedere sia il titolare e non chi gli ha
    trovato il telefono sbloccato."""
    h = _cliente(client, "pwdsbagliata@test.it")

    r = client.request(
        "DELETE", "/api/auth/me", json={"password": "nonlaso"}, headers=h
    )

    assert r.status_code == 401
    db = _db()
    try:
        assert db.query(User).filter(User.email == "pwdsbagliata@test.it").first()
    finally:
        db.close()


def test_it_needs_a_session(client):
    r = client.request("DELETE", "/api/auth/me", json={"password": PWD})
    assert r.status_code == 401


def test_an_admin_cannot_delete_itself_from_here(client, admin_headers):
    """Si chiuderebbe fuori dal suo stesso negozio."""
    r = client.request(
        "DELETE", "/api/auth/me", json={"password": "admin123"}, headers=admin_headers
    )

    assert r.status_code in (401, 403)
