"""Rubrica indirizzi: proprieta', predefinito, limiti."""

INDIRIZZO = {
    "full_name": "Daniele Bucchi",
    "street": "Via Alberto Profeti 271",
    "city": "Cascina",
    "postal_code": "56021",
    "province": "PI",
    "phone": "3463199742",
}


def _register(client, email):
    return client.post(
        "/api/auth/register",
        json={"email": email, "password": "unapasswordlunga"},
    )


def _headers(client, email):
    _register(client, email)
    r = client.post(
        "/api/auth/login",
        data={"username": email, "password": "unapasswordlunga"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _crea(client, headers, **extra):
    body = dict(INDIRIZZO)
    body.update(extra)
    return client.post("/api/addresses", json=body, headers=headers)


# --- base -----------------------------------------------------------------


def test_address_is_saved_and_listed(client):
    h = _headers(client, "rubrica@test.it")

    r = _crea(client, h)
    assert r.status_code == 201, r.text

    elenco = client.get("/api/addresses", headers=h).json()
    assert len(elenco) == 1
    assert elenco[0]["street"] == "Via Alberto Profeti 271"
    assert elenco[0]["phone"] == "3463199742"


def test_the_first_address_becomes_the_default_by_itself(client):
    """Senza, al checkout successivo non ci sarebbe niente da
    precompilare: la rubrica sarebbe piena e la proposta vuota."""
    h = _headers(client, "primo@test.it")

    r = _crea(client, h)

    assert r.json()["is_default"] is True


def test_only_one_address_stays_default(client):
    h = _headers(client, "unosolo@test.it")
    _crea(client, h)
    secondo = _crea(client, h, street="Via Roma 1", is_default=True).json()

    elenco = client.get("/api/addresses", headers=h).json()

    predefiniti = [a for a in elenco if a["is_default"]]
    assert len(predefiniti) == 1
    assert predefiniti[0]["id"] == secondo["id"]


def test_the_default_comes_first_in_the_list(client):
    h = _headers(client, "ordine@test.it")
    primo = _crea(client, h).json()
    _crea(client, h, street="Via Roma 1")
    client.post(f"/api/addresses/{primo['id']}/default", headers=h)

    elenco = client.get("/api/addresses", headers=h).json()

    assert elenco[0]["id"] == primo["id"]


def test_address_can_be_edited(client):
    h = _headers(client, "modifica@test.it")
    a = _crea(client, h).json()

    r = client.put(
        f"/api/addresses/{a['id']}",
        json={**INDIRIZZO, "street": "Via Nuova 9", "label": "Ufficio"},
        headers=h,
    )

    assert r.status_code == 200, r.text
    assert r.json()["street"] == "Via Nuova 9"
    assert r.json()["label"] == "Ufficio"


def test_address_can_be_deleted(client):
    h = _headers(client, "cancella@test.it")
    a = _crea(client, h).json()

    r = client.delete(f"/api/addresses/{a['id']}", headers=h)

    assert r.status_code == 204
    assert client.get("/api/addresses", headers=h).json() == []


def test_deleting_the_default_promotes_another(client):
    """Una rubrica piena senza nessuna proposta non aiuta al checkout."""
    h = _headers(client, "erede@test.it")
    primo = _crea(client, h).json()
    _crea(client, h, street="Via Roma 1")
    client.post(f"/api/addresses/{primo['id']}/default", headers=h)

    client.delete(f"/api/addresses/{primo['id']}", headers=h)

    rimasti = client.get("/api/addresses", headers=h).json()
    assert len(rimasti) == 1
    assert rimasti[0]["is_default"] is True


# --- privatezza -----------------------------------------------------------


def test_addresses_are_private_between_accounts(client):
    """Il filtro e' sempre su utente + id: col solo id basterebbe cambiare
    il numero nell'URL per leggere dove abita un altro."""
    mio = _headers(client, "io@test.it")
    altrui = _headers(client, "altri@test.it")
    a = _crea(client, altrui, street="Via Segreta 1").json()

    assert client.get("/api/addresses", headers=mio).json() == []
    assert client.put(
        f"/api/addresses/{a['id']}", json=INDIRIZZO, headers=mio
    ).status_code == 404
    assert client.delete(
        f"/api/addresses/{a['id']}", headers=mio
    ).status_code == 404
    assert client.post(
        f"/api/addresses/{a['id']}/default", headers=mio
    ).status_code == 404


def test_the_address_book_needs_a_session(client):
    assert client.get("/api/addresses").status_code == 401
    assert client.post("/api/addresses", json=INDIRIZZO).status_code == 401


# --- limiti ---------------------------------------------------------------


def test_street_cannot_be_empty(client):
    h = _headers(client, "vuoto@test.it")
    r = _crea(client, h, street="")
    assert r.status_code == 422


def test_the_ceiling_is_five(client):
    """Fissato di proposito: il test qui sotto legge la costante e
    passerebbe con qualsiasi numero, quindi da solo non proteggerebbe
    il limite da una modifica distratta."""
    from api.addresses import MAX_INDIRIZZI

    assert MAX_INDIRIZZI == 5


def test_there_is_a_ceiling_on_how_many(client):
    from api.addresses import MAX_INDIRIZZI

    h = _headers(client, "troppi@test.it")
    for i in range(MAX_INDIRIZZI):
        assert _crea(client, h, street=f"Via {i}").status_code == 201

    r = _crea(client, h, street="Una di troppo")

    assert r.status_code == 409
