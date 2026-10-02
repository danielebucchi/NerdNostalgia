"""Ordini: spedizione sempre addebitata, token pubblico e stato per il carrello."""
import pytest


@pytest.fixture()
def published_article(client, admin_headers, admin_user):
    return client.post(
        "/api/articles/",
        headers=admin_headers,
        json={
            "user_id": admin_user.id,
            "title": "Game Boy Pocket", "price": 40, "currency": "EUR",
            "condition": "USED", "status": "PUBLISHED", "quantity": 1,
            "shipping_price": 7,
        },
    ).json()


def _payload(article_id, **extra):
    base = {
        "buyer_name": "Mario Rossi", "buyer_email": "mario@test.it",
        # Si spedisce solo a locker: i campi ship_* sono l'indirizzo DEL
        # locker, compilato dalla mappa, non quello di casa del compratore.
        "inpost_point_id": "IT12345",
        "inpost_point_name": "Locker InPost - Conad Livorno",
        "ship_street": "Via Grande 10", "ship_city": "Livorno",
        "ship_postal_code": "57123",
        "items": [{"article_id": article_id, "quantity": 1}],
    }
    base.update(extra)
    return base


def test_shipping_follows_the_bands(client, published_article):
    """La consegna a mano gratuita non esiste piu' (anche da un CAP che prima
    era agevolato, 57xxx = Livorno) e la spedizione segue gli scaglioni sul
    totale, non piu' il prezzo di spedizione del singolo articolo."""
    r = client.post("/api/orders/", json=_payload(published_article["id"]))
    assert r.status_code == 201, r.text
    body = r.json()
    # Articolo da 40 €: sotto i 50 € non si assicura → 6,21 + 4% (1,60) = 7,81.
    # Non i 7 € del vecchio campo spedizione dell'articolo.
    assert float(body["shipping_total"]) == 7.81
    assert float(body["grand_total"]) == 47.81
    assert body["hand_exchange"] is False


def test_hand_exchange_flag_is_ignored(client, published_article):
    """Un client vecchio (o un curioso) che manda ancora hand_exchange=true
    non deve ottenere la spedizione gratis."""
    r = client.post(
        "/api/orders/",
        json=_payload(published_article["id"], hand_exchange=True),
    )
    assert r.status_code == 201, r.text
    assert float(r.json()["shipping_total"]) == 7.81
    assert r.json()["hand_exchange"] is False


def test_create_returns_public_token(client, published_article):
    r = client.post("/api/orders/", json=_payload(published_article["id"]))
    token = r.json()["public_token"]
    assert token and len(token) >= 16


def test_status_endpoint_requires_matching_token(client, published_article):
    created = client.post("/api/orders/", json=_payload(published_article["id"])).json()
    oid, token = created["id"], created["public_token"]

    r = client.get(f"/api/orders/{oid}/status", params={"token": token})
    assert r.status_code == 200
    assert r.json() == {
        "id": oid, "status": "PENDING", "paid": False, "cancelled": False,
    }

    # Token sbagliato: 404 come un ordine inesistente (niente enumerazione)
    r = client.get(f"/api/orders/{oid}/status", params={"token": "x" * 32})
    assert r.status_code == 404

    # Senza token non si passa
    assert client.get(f"/api/orders/{oid}/status").status_code == 422


def test_status_flips_to_paid_after_admin_confirms(
    client, admin_headers, published_article,
):
    """E' questo il segnale che fa svuotare il carrello lato frontend."""
    created = client.post("/api/orders/", json=_payload(published_article["id"])).json()
    oid, token = created["id"], created["public_token"]

    client.patch(
        f"/api/orders/{oid}", headers=admin_headers, json={"status": "PAID"},
    )
    body = client.get(f"/api/orders/{oid}/status", params={"token": token}).json()
    assert body["paid"] is True
    assert body["status"] == "PAID"


def test_cancelled_order_is_flagged_not_paid(
    client, admin_headers, published_article,
):
    created = client.post("/api/orders/", json=_payload(published_article["id"])).json()
    oid, token = created["id"], created["public_token"]

    client.patch(
        f"/api/orders/{oid}", headers=admin_headers, json={"status": "CANCELLED"},
    )
    body = client.get(f"/api/orders/{oid}/status", params={"token": token}).json()
    assert body["paid"] is False
    assert body["cancelled"] is True


# ───────────────── Prenotazione articolo ─────────────────
# Finche' l'ordine e' in attesa il pezzo esce dal catalogo: non e' venduto,
# ma nessun altro deve poterlo comprare.

def _is_in_public_catalog(client, article_id) -> bool:
    items = client.get("/api/articles/?status=PUBLISHED&limit=100").json()["items"]
    return any(a["id"] == article_id for a in items)


def test_order_takes_the_article_out_of_the_catalog(client, published_article):
    aid = published_article["id"]
    assert _is_in_public_catalog(client, aid) is True

    client.post("/api/orders/", json=_payload(aid))

    assert _is_in_public_catalog(client, aid) is False
    # Non e' venduto: e' solo impegnato
    detail = client.get(f"/api/articles/{aid}").json()
    assert detail["status"] == "PUBLISHED"
    assert detail["reserved"] is True


def test_admin_still_sees_reserved_articles(client, published_article):
    aid = published_article["id"]
    client.post("/api/orders/", json=_payload(aid))

    items = client.get(
        "/api/articles/?limit=100&include_reserved=true"
    ).json()["items"]
    assert any(a["id"] == aid and a["reserved"] for a in items)


def test_second_buyer_is_refused(client, published_article):
    """Il pezzo e' unico: il secondo che prova si becca un 409, non un
    secondo ordine sullo stesso oggetto."""
    aid = published_article["id"]
    assert client.post("/api/orders/", json=_payload(aid)).status_code == 201

    second = client.post(
        "/api/orders/",
        json=_payload(aid) | {"buyer_email": "altro@test.it"},
    )
    assert second.status_code == 409
    assert "ordinato" in second.json()["detail"].lower()


def test_paid_order_sells_the_article(client, admin_headers, published_article):
    aid = published_article["id"]
    created = client.post("/api/orders/", json=_payload(aid)).json()

    client.patch(
        f"/api/orders/{created['id']}", headers=admin_headers,
        json={"status": "PAID"},
    )
    detail = client.get(f"/api/articles/{aid}").json()
    assert detail["status"] == "SOLD"
    assert detail["reserved"] is False


def test_cancelled_order_puts_the_article_back_on_sale(
    client, admin_headers, published_article,
):
    aid = published_article["id"]
    created = client.post("/api/orders/", json=_payload(aid)).json()
    assert _is_in_public_catalog(client, aid) is False

    client.patch(
        f"/api/orders/{created['id']}", headers=admin_headers,
        json={"status": "CANCELLED"},
    )
    assert _is_in_public_catalog(client, aid) is True
    detail = client.get(f"/api/articles/{aid}").json()
    assert detail["status"] == "PUBLISHED"
    assert detail["reserved"] is False


def test_release_after_cancel_lets_someone_else_buy(
    client, admin_headers, published_article,
):
    """Il giro completo: ordine abbandonato, annullato, e il pezzo torna
    comprabile da un altro."""
    aid = published_article["id"]
    first = client.post("/api/orders/", json=_payload(aid)).json()
    client.patch(
        f"/api/orders/{first['id']}", headers=admin_headers,
        json={"status": "CANCELLED"},
    )
    second = client.post(
        "/api/orders/", json=_payload(aid) | {"buyer_email": "altro@test.it"},
    )
    assert second.status_code == 201, second.text


def test_free_shipping_over_the_threshold(client, admin_headers, admin_user):
    """Dai 200 € la spedizione sparisce: e' la promessa fatta in home."""
    pricey = client.post(
        "/api/articles/",
        headers=admin_headers,
        json={
            "user_id": admin_user.id,
            "title": "Console da collezione", "price": 250, "currency": "EUR",
            "condition": "USED", "status": "PUBLISHED", "quantity": 1,
            "shipping_price": 12,
        },
    ).json()

    body = client.post("/api/orders/", json=_payload(pricey["id"])).json()
    assert float(body["shipping_total"]) == 0.0
    assert float(body["grand_total"]) == 250.0


def test_shipping_is_computed_on_the_whole_order(
    client, admin_headers, admin_user,
):
    """Lo scaglione guarda il totale del carrello, non i singoli pezzi: due
    articoli da 60 € fanno 120 €, che e' sopra la soglia dell'assicurazione:
    una sola spedizione assicurata, non due."""
    def make(title, price):
        return client.post(
            "/api/articles/", headers=admin_headers,
            json={
                "user_id": admin_user.id, "title": title, "price": price,
                "currency": "EUR", "condition": "USED", "status": "PUBLISHED",
                "quantity": 1,
            },
        ).json()

    a, b = make("Primo", 60), make("Secondo", 60)
    body = client.post("/api/orders/", json={
        "buyer_name": "Mario Rossi", "buyer_email": "mario@test.it",
        "inpost_point_id": "IT12345",
        "ship_street": "Via Grande 10", "ship_city": "Livorno",
        "ship_postal_code": "57123",
        "items": [
            {"article_id": a["id"], "quantity": 1},
            {"article_id": b["id"], "quantity": 1},
        ],
    }).json()

    # 120 € → base 6,21 + 4% (4,80) = 11,01, piu' assicurazione 5,90 (attiva
    # di default sopra i 50 €) = 16,91
    assert float(body["subtotal"]) == 120.0
    assert float(body["shipping_total"]) == 16.91
    assert body["insured"] is True


# ───────────────── Locker InPost ─────────────────

def _without_locker(article_id):
    payload = _payload(article_id)
    del payload["inpost_point_id"]
    del payload["inpost_point_name"]
    return payload


def test_without_inpost_token_the_order_goes_through_without_a_locker(
    client, published_article, monkeypatch,
):
    """Senza token InPost il sito ripiega sulla consegna a domicilio: se
    bloccassimo l'ordine, nessuno potrebbe comprare mentre si aspetta il
    contratto con InPost."""
    monkeypatch.delenv("INPOST_GEOWIDGET_TOKEN", raising=False)

    r = client.post("/api/orders/", json=_without_locker(published_article["id"]))
    assert r.status_code == 201, r.text
    assert r.json()["inpost_point_id"] is None


def test_with_inpost_token_the_locker_becomes_mandatory(
    client, admin_headers, admin_user, monkeypatch,
):
    """Con la mappa attiva si spedisce solo a locker: senza punto scelto
    l'ordine viene rifiutato (articolo nuovo, cosi' il 400 non si confonde
    con il 409 della prenotazione)."""
    monkeypatch.setenv("INPOST_GEOWIDGET_TOKEN", "tok-test")
    fresh = client.post(
        "/api/articles/", headers=admin_headers,
        json={
            "user_id": admin_user.id, "title": "Pezzo libero", "price": 20,
            "currency": "EUR", "condition": "USED", "status": "PUBLISHED",
            "quantity": 1,
        },
    ).json()

    r = client.post("/api/orders/", json=_without_locker(fresh["id"]))
    assert r.status_code == 400, r.text
    assert "locker" in r.json()["detail"].lower()

    # Con il locker scelto, lo stesso articolo si ordina senza problemi
    ok = client.post("/api/orders/", json=_payload(fresh["id"]))
    assert ok.status_code == 201, ok.text


def test_locker_is_saved_on_the_order(client, published_article):
    body = client.post("/api/orders/", json=_payload(published_article["id"])).json()
    assert body["inpost_point_id"] == "IT12345"
    assert body["inpost_point_name"] == "Locker InPost - Conad Livorno"
    # ship_* e' l'indirizzo del locker: e' li' che va il pacco
    assert body["ship_city"] == "Livorno"
    assert body["ship_postal_code"] == "57123"


# ───────────────── Assicurazione spedizione ─────────────────

def test_insurance_defaults_off_below_fifty(client, published_article):
    """Articolo da 40 €: sotto soglia, non assicurato di default."""
    body = client.post("/api/orders/", json=_payload(published_article["id"])).json()
    assert body["insured"] is False
    assert float(body["insurance_fee"]) == 0.0
    assert float(body["shipping_total"]) == 7.81


def test_buyer_can_insure_a_small_order(client, published_article):
    """Il compratore puo' assicurare anche sotto i 50 €, pagando di piu'."""
    body = client.post(
        "/api/orders/",
        json=_payload(published_article["id"]) | {"insured": True},
    ).json()
    assert body["insured"] is True
    assert float(body["insurance_fee"]) == 5.90
    assert float(body["shipping_total"]) == 13.71   # 7,81 + 5,90
    assert float(body["grand_total"]) == 53.71      # 40 + 13,71


def test_buyer_can_decline_insurance_on_a_big_order(
    client, admin_headers, admin_user,
):
    """E puo' rinunciare sopra i 50 €, risparmiando."""
    art = client.post(
        "/api/articles/", headers=admin_headers,
        json={
            "user_id": admin_user.id, "title": "Console", "price": 100,
            "currency": "EUR", "condition": "USED", "status": "PUBLISHED",
            "quantity": 1,
        },
    ).json()

    body = client.post(
        "/api/orders/", json=_payload(art["id"]) | {"insured": False},
    ).json()
    assert body["insured"] is False
    assert float(body["shipping_total"]) == 10.21   # solo base, niente premio


def test_free_shipping_orders_are_always_insured(
    client, admin_headers, admin_user,
):
    """Sopra i 250 € la spedizione e' gratis E assicurata: un pacco di quel
    valore non lo mandiamo scoperto, e il premio lo paghiamo noi."""
    art = client.post(
        "/api/articles/", headers=admin_headers,
        json={
            "user_id": admin_user.id, "title": "Pezzo raro", "price": 300,
            "currency": "EUR", "condition": "USED", "status": "PUBLISHED",
            "quantity": 1,
        },
    ).json()

    body = client.post(
        "/api/orders/", json=_payload(art["id"]) | {"insured": False},
    ).json()
    # La rinuncia viene ignorata: resta assicurato, ma non costa nulla
    assert body["insured"] is True
    assert float(body["insurance_fee"]) == 0.0
    assert float(body["shipping_total"]) == 0.0


def test_free_shipping_switch_zeroes_everything(
    client, admin_headers, published_article,
):
    """L'interruttore di /admin/impostazioni azzera la riga spedizione, premio
    assicurativo compreso: e' una promozione, non uno sconto per ordine."""
    # Prima: tariffa normale
    before = client.post("/api/orders/", json=_payload(published_article["id"]))
    assert float(before.json()["shipping_total"]) == 7.81

    client.put(
        "/api/settings/", headers=admin_headers,
        json={"values": {"free_shipping_all": "true"}},
    )
    # L'articolo e' prenotato dal primo ordine: ne serve un altro
    art = client.post(
        "/api/articles/", headers=admin_headers,
        json={
            "user_id": 1, "title": "Secondo pezzo", "price": 120,
            "currency": "EUR", "condition": "USED", "status": "PUBLISHED",
            "quantity": 1,
        },
    ).json()

    body = client.post(
        "/api/orders/", json=_payload(art["id"]) | {"insured": True},
    ).json()
    assert float(body["shipping_total"]) == 0.0
    assert float(body["insurance_fee"]) == 0.0
    assert float(body["grand_total"]) == 120.0

