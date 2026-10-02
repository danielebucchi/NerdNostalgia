"""Recupero password: token monouso, a scadenza, che non rivela chi e' iscritto."""
from datetime import datetime, timedelta, timezone


def _register(client, email, password="unapasswordlunga"):
    return client.post(
        "/api/auth/register", json={"email": email, "password": password}
    )


def _login(client, email, password):
    return client.post(
        "/api/auth/login", data={"username": email, "password": password}
    )


def _token_di(client, email, monkeypatch=None):
    """Intercetta il token come farebbe il link dentro l'email."""
    from utils import mailer

    visti = []
    originale = mailer.password_reset
    mailer.password_reset = lambda user_id, token: visti.append(token)
    try:
        r = client.post("/api/auth/forgot-password", json={"email": email})
        assert r.status_code == 200, r.text
    finally:
        mailer.password_reset = originale
    return visti[0] if visti else None


# --- il giro che funziona -------------------------------------------------


def test_the_link_lets_you_set_a_new_password(client):
    _register(client, "scordata@test.it")
    tok = _token_di(client, "scordata@test.it")

    r = client.post(
        "/api/auth/reset-password",
        json={"token": tok, "password": "unanuovapasswordlunga"},
    )

    assert r.status_code == 200, r.text
    assert _login(client, "scordata@test.it", "unanuovapasswordlunga").status_code == 200


def test_the_old_password_stops_working(client):
    _register(client, "vecchia@test.it")
    tok = _token_di(client, "vecchia@test.it")

    client.post(
        "/api/auth/reset-password",
        json={"token": tok, "password": "unanuovapasswordlunga"},
    )

    assert _login(client, "vecchia@test.it", "unapasswordlunga").status_code == 401


# --- il token --------------------------------------------------------------


def test_the_link_works_only_once(client):
    """Se e' finito in mano a qualcun altro, dopo il primo uso non serve
    piu' a niente."""
    _register(client, "unavolta@test.it")
    tok = _token_di(client, "unavolta@test.it")
    client.post(
        "/api/auth/reset-password",
        json={"token": tok, "password": "unanuovapasswordlunga"},
    )

    r = client.post(
        "/api/auth/reset-password",
        json={"token": tok, "password": "unaterzapasswordlunga"},
    )

    assert r.status_code == 400


def test_an_expired_link_is_refused(client):
    """Un link che vale per sempre e' una seconda password permanente,
    dimenticata in fondo a una casella di posta."""
    from main import app
    from models.db import User
    from utils.session import get_db

    _register(client, "scaduto@test.it")
    tok = _token_di(client, "scaduto@test.it")

    db = next(app.dependency_overrides[get_db]())
    try:
        u = db.query(User).filter(User.email == "scaduto@test.it").first()
        u.reset_token_expires_at = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    r = client.post(
        "/api/auth/reset-password",
        json={"token": tok, "password": "unanuovapasswordlunga"},
    )

    assert r.status_code == 400


def test_an_invented_token_is_refused(client):
    r = client.post(
        "/api/auth/reset-password",
        json={"token": "inventato-di-sana-pianta-lungo", "password": "unanuovapasswordlunga"},
    )
    assert r.status_code == 400


def test_asking_again_invalidates_the_previous_link(client):
    """Due link validi insieme raddoppiano le occasioni di perderne uno."""
    _register(client, "duevolte@test.it")
    primo = _token_di(client, "duevolte@test.it")
    _token_di(client, "duevolte@test.it")

    r = client.post(
        "/api/auth/reset-password",
        json={"token": primo, "password": "unanuovapasswordlunga"},
    )

    assert r.status_code == 400


def test_the_token_is_not_stored_in_clear(client):
    """Chi legge il database non deve poter entrare in tutti gli account."""
    from main import app
    from models.db import User
    from utils.session import get_db

    _register(client, "inchiaro@test.it")
    tok = _token_di(client, "inchiaro@test.it")

    db = next(app.dependency_overrides[get_db]())
    try:
        u = db.query(User).filter(User.email == "inchiaro@test.it").first()
        assert u.reset_token_hash
        assert u.reset_token_hash != tok
        assert tok not in u.reset_token_hash
    finally:
        db.close()


# --- niente spie su chi e' iscritto ---------------------------------------


def test_an_unknown_email_gets_the_same_answer(client):
    _register(client, "esiste@test.it")

    noto = client.post("/api/auth/forgot-password", json={"email": "esiste@test.it"})
    ignoto = client.post(
        "/api/auth/forgot-password", json={"email": "mai-visto@test.it"}
    )

    assert noto.status_code == ignoto.status_code == 200
    assert noto.json() == ignoto.json()


def test_an_unknown_email_gets_no_token(client):
    assert _token_di(client, "nessuno@test.it") is None


# --- la nuova password -----------------------------------------------------


def test_a_short_new_password_is_refused(client):
    _register(client, "corta@test.it")
    tok = _token_di(client, "corta@test.it")

    r = client.post("/api/auth/reset-password", json={"token": tok, "password": "breve"})

    assert r.status_code == 422
