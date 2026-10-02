"""Consenso promozionale: revoca dal link email e interruttore nel profilo.

Un consenso che non si puo' ritirare con la stessa facilita' con cui si da'
non e' valido (art. 7.3 GDPR): da qui le due strade, il token senza login e
la spunta nel profilo.
"""


def _register(client, email, **extra):
    body = {"email": email, "password": "unapasswordlunga"}
    body.update(extra)
    return client.post("/api/auth/register", json=body)


def _token(client, email):
    r = client.post(
        "/api/auth/login",
        data={"username": email, "password": "unapasswordlunga"},
    )
    return r.json()["access_token"]


def _headers(client, email):
    return {"Authorization": f"Bearer {_token(client, email)}"}


def _unsubscribe_token(client, admin_headers, email):
    """Il token non esce da nessuna API pubblica: lo leggo dal database,
    come farebbe il link dentro l'email."""
    from models.db import User
    from utils.session import SessionLocal  # noqa: F401  (override nei test)

    users = client.get("/api/users/", headers=admin_headers).json()
    assert any(u["email"] == email for u in users)
    # Il valore vero sta nella sessione di test: lo recupero via la stessa
    # dependency usata dall'app.
    from main import app
    from utils.session import get_db

    db = next(app.dependency_overrides[get_db]())
    try:
        return db.query(User).filter(User.email == email).first().unsubscribe_token
    finally:
        db.close()


# --- revoca dal link nelle email ------------------------------------------


def test_unsubscribe_link_turns_consent_off(client, admin_headers):
    _register(client, "revoca@test.it", marketing_consent=True)
    tok = _unsubscribe_token(client, admin_headers, "revoca@test.it")

    r = client.post(
        "/api/auth/unsubscribe",
        json={"token": tok, "marketing_consent": False},
    )

    assert r.status_code == 200, r.text
    assert r.json()["marketing_consent"] is False


def test_unsubscribe_needs_no_password(client, admin_headers):
    """Chi vuole smettere di ricevere email non deve prima ricordarsi la
    password: la richiesta va a buon fine senza nessun header."""
    _register(client, "senzalogin@test.it", marketing_consent=True)
    tok = _unsubscribe_token(client, admin_headers, "senzalogin@test.it")

    r = client.post(
        "/api/auth/unsubscribe",
        json={"token": tok, "marketing_consent": False},
    )

    assert r.status_code == 200, r.text


def test_unsubscribe_hides_the_full_address(client, admin_headers):
    """La pagina deve far riconoscere l'indirizzo senza mostrarlo: il link
    gira nella posta e resta nella cronologia del browser."""
    _register(client, "mariorossi@test.it", marketing_consent=True)
    tok = _unsubscribe_token(client, admin_headers, "mariorossi@test.it")

    r = client.post(
        "/api/auth/unsubscribe",
        json={"token": tok, "marketing_consent": False},
    )

    email = r.json()["email"]
    assert "mariorossi" not in email
    assert email.endswith("@test.it")


def test_the_same_link_undoes_an_accidental_click(client, admin_headers):
    _register(client, "ripensamento@test.it", marketing_consent=True)
    tok = _unsubscribe_token(client, admin_headers, "ripensamento@test.it")
    client.post("/api/auth/unsubscribe", json={"token": tok, "marketing_consent": False})

    r = client.post(
        "/api/auth/unsubscribe",
        json={"token": tok, "marketing_consent": True},
    )

    assert r.json()["marketing_consent"] is True


def test_unknown_token_is_refused(client):
    r = client.post(
        "/api/auth/unsubscribe",
        json={"token": "non-esiste-proprio", "marketing_consent": False},
    )
    assert r.status_code == 404


def test_empty_token_is_refused(client):
    """Senza questo, un token vuoto rischierebbe di pescare il primo
    account che non ne ha uno."""
    r = client.post(
        "/api/auth/unsubscribe",
        json={"token": "", "marketing_consent": False},
    )
    assert r.status_code == 422


# --- interruttore nel profilo ---------------------------------------------


def test_profile_reports_the_current_choice(client):
    _register(client, "spunta@test.it", marketing_consent=True)

    r = client.get(
        "/api/auth/me/marketing-consent", headers=_headers(client, "spunta@test.it")
    )

    assert r.status_code == 200, r.text
    assert r.json()["marketing_consent"] is True


def test_profile_can_turn_consent_on_and_off(client):
    _register(client, "interruttore@test.it")
    h = _headers(client, "interruttore@test.it")

    acceso = client.put(
        "/api/auth/me/marketing-consent", json={"marketing_consent": True}, headers=h
    )
    assert acceso.json()["marketing_consent"] is True

    spento = client.put(
        "/api/auth/me/marketing-consent", json={"marketing_consent": False}, headers=h
    )
    assert spento.json()["marketing_consent"] is False


def test_consent_given_from_the_profile_gets_a_working_link(client, admin_headers):
    """Chi accetta dal profilo deve poter uscire dal link in fondo alla
    prima email: senza token, quel link non porterebbe da nessuna parte."""
    _register(client, "tokentardivo@test.it")
    client.put(
        "/api/auth/me/marketing-consent",
        json={"marketing_consent": True},
        headers=_headers(client, "tokentardivo@test.it"),
    )

    tok = _unsubscribe_token(client, admin_headers, "tokentardivo@test.it")

    assert tok
    r = client.post(
        "/api/auth/unsubscribe", json={"token": tok, "marketing_consent": False}
    )
    assert r.status_code == 200, r.text


def test_the_switch_needs_a_session(client):
    r = client.put(
        "/api/auth/me/marketing-consent", json={"marketing_consent": False}
    )
    assert r.status_code == 401
