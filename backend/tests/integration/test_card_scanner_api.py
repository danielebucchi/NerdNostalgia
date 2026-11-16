"""Scanner carte: dallo scan alla collezione, dalla collezione alla vendita.

CardTrader, eBay e Tesseract sono finti: mettere in vendita carte vere
mentre si prova il codice vorrebbe dire vendere carte che non esistono.
"""
import io

import pytest
from PIL import Image

from models.db import CardBlueprint, CardScan, PersonalCard
from utils import card_index as ci
from utils.card_ocr import LetturaCarta


@pytest.fixture(autouse=True)
def mondo_finto(monkeypatch, tmp_path, db_session):
    from utils import card_ocr, cardtrader_client as ct, ebay_client as eb, storage

    # Uploads in una cartella del test, con la stessa struttura del vero
    # (uploads/<scope>/<id>/...): gli URL /static/... devono risolversi.
    monkeypatch.setattr(storage, "UPLOADS_DIR", tmp_path)
    for scope in ("scans", "articles"):
        monkeypatch.setitem(storage._SCOPES, scope, tmp_path / scope)

    monkeypatch.setattr(ct, "is_configured", lambda: True)
    monkeypatch.setattr(card_ocr, "is_available", lambda: True)
    monkeypatch.setattr(ct, "expansions_cached", lambda ttl=3600: [
        {"id": 1, "game_id": 5, "code": "ssp", "name": "Surging Sparks"},
    ])
    # La carta "letta" dallo scan
    monkeypatch.setattr(card_ocr, "read_card", lambda raw, hint=None, appreso=None: (
        Image.new("RGB", (63, 88), "white"),
        LetturaCarta(number="004", total="191", set_codes=["SSP"], language="it",
                     printed_code="004/191", name_text="Durant ex"),
    ))
    prodotti = []
    monkeypatch.setattr(ct, "suggested_price_cents", lambda bp, pos, **kw: {
        "cents": 400, "position": 2, "total": 9, "all_cents": [], "filtered": True})
    monkeypatch.setattr(ct, "create_product", lambda **kw: prodotti.append(kw) or {"resource": {"id": 777}})
    monkeypatch.setattr(ct, "delete_product", lambda pid: None)
    aggiornati = []
    monkeypatch.setattr(ct, "update_product", lambda pid, **kw: aggiornati.append((pid, kw)))
    monkeypatch.setattr(eb, "has_app_credentials", lambda: True)
    monkeypatch.setattr(eb, "sold_items_search", lambda q, **kw: [
        {"title": f"Durant ex 004/191 #{i}", "lastSoldPrice": {"value": "6.00", "currency": "EUR"},
         "lastSoldDate": f"2026-11-{i + 1:02d}T10:00:00Z"} for i in range(12)
    ])

    db_session.add(CardBlueprint(
        id=10, game_id=5, expansion_id=1, expansion_code="ssp", expansion_name="Surging Sparks",
        name="Durant ex", collector_number="004", number_norm="4", dhash="f" * 64,
        editable="first_edition,pokemon_language:en|it,pokemon_reverse",
    ))
    # L'analisi vera scaricherebbe l'immagine da CardTrader: qui la si
    # decide a tavolino.
    from utils import card_features
    analisi = {
        "supports": {"reverse": True, "first_edition": True},
        "reverse": {"value": True, "score": 1.9},
        "first_edition": {"value": None, "score": 0.02},
        "condition": {"value": "Slightly Played", "wear_front": 0.01},
    }
    monkeypatch.setattr(card_features, "analyze", lambda *a, **kw: dict(analisi))
    db_session.commit()
    return prodotti


def _carica(client, admin_headers):
    buf = io.BytesIO()
    Image.new("RGB", (630, 880), "white").save(buf, format="PNG")
    return client.post(
        "/api/card-scanner/scans",
        files={"file": ("scan001.png", buf.getvalue(), "image/png")},
        data={"game_id": "5"},
        headers=admin_headers,
    )


def test_scan_proposes_the_card(client, admin_headers):
    r = _carica(client, admin_headers)
    assert r.status_code == 201, r.text
    scan = r.json()
    assert scan["status"] == "PENDING"
    assert scan["candidates"][0]["blueprint_id"] == 10
    assert scan["ocr"]["printed_code"] == "004/191"
    assert "/static/scans/" in scan["image_url"]


def test_confirmed_scan_enters_the_collection_priced(client, admin_headers, db_session):
    scan = _carica(client, admin_headers).json()
    r = client.post(f"/api/card-scanner/scans/{scan['id']}/confirm",
                    json={"blueprint_id": 10, "condition": "Near Mint"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    carta = r.json()
    assert carta["name"] == "Durant ex"
    assert carta["printed_code"] == "004/191"
    assert carta["language"] == "it"
    assert carta["status"] == "IN_STOCK"
    assert float(carta["cardtrader_price"]) == 4.0
    assert float(carta["ebay_sold_avg"]) == 6.0
    assert carta["ebay_sold_count"] == 10
    # Suggerito = in mezzo, e diventa il prezzo di vendita di partenza
    assert float(carta["estimated_value"]) == 5.0
    assert float(carta["list_price"]) == 5.0

    assert db_session.get(CardScan, scan["id"]).status == "CONFIRMED"
    assert client.get("/api/card-scanner/scans", headers=admin_headers).json() == []


def test_scan_comes_with_the_analysis_of_the_top_card(client, admin_headers):
    scan = _carica(client, admin_headers).json()
    assert scan["features"]["blueprint_id"] == 10
    assert scan["features"]["reverse"]["value"] is True


def test_confirm_without_choices_uses_the_analysis(client, admin_headers):
    """Reverse sicuro → reverse; prima edizione incerta → no; condizione
    stimata → quella."""
    scan = _carica(client, admin_headers).json()
    carta = client.post(f"/api/card-scanner/scans/{scan['id']}/confirm",
                        json={"blueprint_id": 10, "price_now": False}, headers=admin_headers).json()
    assert carta["reverse"] is True
    assert carta["first_edition"] is False
    assert carta["condition"] == "Slightly Played"


def test_explicit_choices_win_over_the_analysis(client, admin_headers):
    scan = _carica(client, admin_headers).json()
    carta = client.post(f"/api/card-scanner/scans/{scan['id']}/confirm",
                        json={"blueprint_id": 10, "price_now": False, "reverse": False,
                              "condition": "Near Mint"}, headers=admin_headers).json()
    assert carta["reverse"] is False
    assert carta["condition"] == "Near Mint"


def test_back_scan_joins_the_photos(client, admin_headers):
    scan = _carica(client, admin_headers).json()
    buf = io.BytesIO()
    Image.new("RGB", (630, 880), "navy").save(buf, format="PNG")
    r = client.post(f"/api/card-scanner/scans/{scan['id']}/back",
                    files={"file": ("scan001_retro.png", buf.getvalue(), "image/png")},
                    headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["back_image_url"]
    carta = client.post(f"/api/card-scanner/scans/{scan['id']}/confirm",
                        json={"blueprint_id": 10, "price_now": False}, headers=admin_headers).json()
    assert len(carta["images"]) == 2


def test_scan_cannot_be_confirmed_twice(client, admin_headers):
    scan = _carica(client, admin_headers).json()
    url = f"/api/card-scanner/scans/{scan['id']}/confirm"
    client.post(url, json={"blueprint_id": 10, "price_now": False}, headers=admin_headers)
    r = client.post(url, json={"blueprint_id": 10, "price_now": False}, headers=admin_headers)
    assert r.status_code == 409


def test_manual_ebay_prices_replace_the_api(client, admin_headers, db_session):
    scan = _carica(client, admin_headers).json()
    carta = client.post(f"/api/card-scanner/scans/{scan['id']}/confirm",
                        json={"blueprint_id": 10}, headers=admin_headers).json()
    r = client.post(f"/api/card-scanner/cards/{carta['id']}/ebay-sold",
                    json={"prices": "8,00 10 12"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert float(r.json()["card"]["ebay_sold_avg"]) == 10.0
    assert float(r.json()["card"]["estimated_value"]) == 7.0
    # Una nuova valutazione non cancella i venduti scritti a mano
    r = client.post(f"/api/card-scanner/cards/{carta['id']}/price", headers=admin_headers)
    assert r.json()["card"]["ebay_sold_source"] == "manuale"
    assert float(r.json()["card"]["ebay_sold_avg"]) == 10.0


def test_publish_on_cardtrader_at_the_chosen_price(client, admin_headers, mondo_finto):
    scan = _carica(client, admin_headers).json()
    carta = client.post(f"/api/card-scanner/scans/{scan['id']}/confirm",
                        json={"blueprint_id": 10, "price_now": False}, headers=admin_headers).json()
    client.patch(f"/api/personal-cards/{carta['id']}", json={"list_price": "4.50"}, headers=admin_headers)

    r = client.post(f"/api/card-scanner/cards/{carta['id']}/cardtrader", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["product_id"] == 777
    assert mondo_finto[0]["price_eur"] == 4.5
    assert mondo_finto[0]["language"] == "it"

    r = client.delete(f"/api/card-scanner/cards/{carta['id']}/cardtrader", headers=admin_headers)
    assert r.status_code == 200


def test_no_price_no_listing(client, admin_headers):
    scan = _carica(client, admin_headers).json()
    carta = client.post(f"/api/card-scanner/scans/{scan['id']}/confirm",
                        json={"blueprint_id": 10, "price_now": False}, headers=admin_headers).json()
    r = client.post(f"/api/card-scanner/cards/{carta['id']}/cardtrader", headers=admin_headers)
    assert r.status_code == 400
    assert "prezzo" in r.json()["detail"]


def test_ebay_needs_settings_before_publishing(client, admin_headers, monkeypatch):
    from utils import ebay_client as eb
    monkeypatch.setattr(eb, "is_configured", lambda: True)
    scan = _carica(client, admin_headers).json()
    carta = client.post(f"/api/card-scanner/scans/{scan['id']}/confirm",
                        json={"blueprint_id": 10}, headers=admin_headers).json()
    r = client.post(f"/api/card-scanner/cards/{carta['id']}/ebay", headers=admin_headers)
    assert r.status_code == 400
    assert "Impostazioni eBay" in r.json()["detail"]


def test_csv_export(client, admin_headers):
    scan = _carica(client, admin_headers).json()
    client.post(f"/api/card-scanner/scans/{scan['id']}/confirm",
                json={"blueprint_id": 10}, headers=admin_headers)
    r = client.get("/api/card-scanner/cards/export.csv", headers=admin_headers)
    assert r.status_code == 200
    righe = r.text.lstrip("﻿").splitlines()
    assert righe[0].startswith("id;nome;espansione;numero")
    assert "Durant ex;Surging Sparks;004/191;it;Slightly Played;1;;si;" in righe[1]
    assert ";5,00;" in righe[1]


def test_folder_uploads_follow_the_session_chosen_in_the_page(client, admin_headers, db_session):
    """Lo script della cartella non manda il gioco: vale quello della pagina."""
    r = client.put("/api/card-scanner/session", json={"game_id": 5, "expansion_id": 1},
                   headers=admin_headers)
    assert r.status_code == 200, r.text
    buf = io.BytesIO()
    Image.new("RGB", (630, 880), "white").save(buf, format="PNG")
    r = client.post("/api/card-scanner/scans",
                    files={"file": ("carta12.jpg", buf.getvalue(), "image/jpeg")},
                    headers=admin_headers)
    assert r.status_code == 201, r.text
    assert (r.json()["game_id"], r.json()["expansion_id"]) == (5, 1)
    assert client.get("/api/card-scanner/status", headers=admin_headers).json()["session"] == \
        {"game_id": 5, "expansion_id": 1}


def test_card_can_be_deleted_with_its_scan(client, admin_headers, db_session):
    scan = _carica(client, admin_headers).json()
    carta = client.post(f"/api/card-scanner/scans/{scan['id']}/confirm",
                        json={"blueprint_id": 10}, headers=admin_headers).json()
    r = client.delete(f"/api/card-scanner/cards/{carta['id']}", headers=admin_headers)
    assert r.status_code == 204, r.text
    assert client.get("/api/card-scanner/cards", headers=admin_headers).json() == []
    assert db_session.get(CardScan, scan["id"]) is None


def test_card_on_sale_must_be_withdrawn_first(client, admin_headers):
    scan = _carica(client, admin_headers).json()
    carta = client.post(f"/api/card-scanner/scans/{scan['id']}/confirm",
                        json={"blueprint_id": 10}, headers=admin_headers).json()
    client.post(f"/api/card-scanner/cards/{carta['id']}/cardtrader", headers=admin_headers)
    r = client.delete(f"/api/card-scanner/cards/{carta['id']}", headers=admin_headers)
    assert r.status_code == 409
    assert "ritirala" in r.json()["detail"]


# --- sito ---------------------------------------------------------------


def _carta_confermata(client, admin_headers):
    scan = _carica(client, admin_headers).json()
    return client.post(f"/api/card-scanner/scans/{scan['id']}/confirm",
                       json={"blueprint_id": 10}, headers=admin_headers).json()


def test_card_goes_on_the_site_with_the_scan_photos(client, admin_headers, db_session):
    from models.db import Article, ArticleStatus
    carta = _carta_confermata(client, admin_headers)
    r = client.post(f"/api/card-scanner/cards/{carta['id']}/site", headers=admin_headers)
    assert r.status_code == 200, r.text
    art = db_session.get(Article, r.json()["article_id"])
    assert art.status == ArticleStatus.PUBLISHED
    assert float(art.price) == 5.0
    assert "Durant ex" in art.title and "004/191" in art.title
    assert len(art.images) == 1 and "/static/articles/" in art.images[0]
    assert art.card_language == "it"

    card = client.get("/api/card-scanner/cards", headers=admin_headers).json()[0]
    assert card["site_status"] == "PUBLISHED"
    # Ripubblicare aggiorna lo stesso articolo, non ne crea un altro
    client.patch(f"/api/personal-cards/{carta['id']}", json={"list_price": "7.00"}, headers=admin_headers)
    r2 = client.post(f"/api/card-scanner/cards/{carta['id']}/site", headers=admin_headers)
    assert r2.json()["article_id"] == art.id
    db_session.refresh(art)
    assert float(art.price) == 7.0


def test_withdrawn_from_the_site_is_archived_not_deleted(client, admin_headers, db_session):
    from models.db import Article, ArticleStatus
    carta = _carta_confermata(client, admin_headers)
    art_id = client.post(f"/api/card-scanner/cards/{carta['id']}/site", headers=admin_headers).json()["article_id"]
    assert client.delete(f"/api/card-scanner/cards/{carta['id']}", headers=admin_headers).status_code == 409
    client.delete(f"/api/card-scanner/cards/{carta['id']}/site", headers=admin_headers)
    assert db_session.get(Article, art_id).status == ArticleStatus.ARCHIVED


def test_sold_on_the_site_is_sold_in_the_collection_and_withdrawn(client, admin_headers, db_session, monkeypatch):
    from utils import cardtrader_client as ct
    ritirate = []
    monkeypatch.setattr(ct, "delete_product", lambda pid: ritirate.append(pid))
    carta = _carta_confermata(client, admin_headers)
    client.post(f"/api/card-scanner/cards/{carta['id']}/cardtrader", headers=admin_headers)
    art_id = client.post(f"/api/card-scanner/cards/{carta['id']}/site", headers=admin_headers).json()["article_id"]

    r = client.post(f"/api/articles/{art_id}/sell", headers=admin_headers)
    assert r.status_code == 200, r.text
    card = db_session.get(PersonalCard, carta["id"])
    db_session.refresh(card)
    assert card.status == "SOLD" and card.sold_platform == "sito"
    assert ritirate == [777]
    assert card.cardtrader_product_id is None


def test_collection_card_is_not_pushed_to_cardtrader_twice(client, admin_headers, db_session):
    from models.db import Article
    from utils import cardtrader_sync as cts
    carta = _carta_confermata(client, admin_headers)
    art_id = client.post(f"/api/card-scanner/cards/{carta['id']}/site", headers=admin_headers).json()["article_id"]
    esito = cts.auto_publish_if_card(db_session, db_session.get(Article, art_id))
    assert esito["status"] == "skipped"


# --- memoria ------------------------------------------------------------


def test_second_copy_is_recognised_from_the_first_confirmed_scan(client, admin_headers, db_session, monkeypatch):
    """L'OCR non legge niente e l'immagine CardTrader non somiglia: la
    prima volta si cerca a mano, la seconda la carta e' gia' nota."""
    from utils import card_ocr
    db_session.add(CardBlueprint(
        id=11, game_id=5, expansion_id=1, expansion_code="ssp", expansion_name="Surging Sparks",
        name="Scatterbug", collector_number="005", number_norm="5", dhash="0f" * 32,
        editable="pokemon_language:en|it",
    ))
    db_session.commit()
    monkeypatch.setattr(card_ocr, "read_card", lambda raw, hint=None, appreso=None: (
        Image.new("RGB", (63, 88), "white"), LetturaCarta(),
    ))
    prima = _carica(client, admin_headers).json()
    assert not any(c["blueprint_id"] == 11 for c in prima["candidates"])
    client.post(f"/api/card-scanner/scans/{prima['id']}/confirm",
                json={"blueprint_id": 11, "price_now": False}, headers=admin_headers)

    seconda = _carica(client, admin_headers).json()
    assert seconda["candidates"][0]["blueprint_id"] == 11
    assert seconda["candidates"][0]["seen_before"] == 1.0
    assert seconda["confidence"] == "alta"
    stato = client.get("/api/card-scanner/status", headers=admin_headers).json()
    assert stato["learning"]["references"] == 1


# --- conferma automatica (script giornaliero) -----------------------------


def test_sure_scan_goes_into_the_collection_by_itself(client, admin_headers, db_session):
    # L'immagine CardTrader uguale allo scan: riconoscimento davvero sicuro
    db_session.get(CardBlueprint, 10).dhash = ci.dhash(Image.new("RGB", (63, 88), "white"))
    db_session.commit()
    scan = _carica(client, admin_headers).json()
    assert scan["confidence"] == "alta"
    r = client.post(f"/api/card-scanner/scans/{scan['id']}/auto-confirm?price_now=false", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["confirmed"] is True
    assert r.json()["card"]["name"] == "Durant ex"
    # Rifarlo non crea un doppione
    r = client.post(f"/api/card-scanner/scans/{scan['id']}/auto-confirm", headers=admin_headers)
    assert r.json()["confirmed"] is False
    assert len(client.get("/api/card-scanner/cards", headers=admin_headers).json()) == 1


def test_unsure_scan_waits_for_a_person(client, admin_headers, monkeypatch):
    from utils import card_ocr
    monkeypatch.setattr(card_ocr, "read_card", lambda raw, hint=None, appreso=None: (
        Image.new("RGB", (63, 88), "white"), LetturaCarta(name_text="Durant ex"),
    ))
    scan = _carica(client, admin_headers).json()
    r = client.post(f"/api/card-scanner/scans/{scan['id']}/auto-confirm", headers=admin_headers).json()
    assert r["confirmed"] is False and "confidenza" in r["reason"]
    assert [s["id"] for s in client.get("/api/card-scanner/scans", headers=admin_headers).json()] == [scan["id"]]


def test_windows_kit_is_ready_to_install(client, admin_headers):
    import zipfile
    r = client.get("/api/card-scanner/windows-kit", headers=admin_headers)
    assert r.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(r.content))
    nomi = {n.split("/", 1)[1] for n in z.namelist()}
    assert {"Installa.cmd", "Installa.ps1", "scanner_sync.py", "predefiniti.ini", "LEGGIMI.txt"} <= nomi
    # A capo Windows nei .cmd, e l'indirizzo del sito gia' scritto
    assert b"\r\n" in z.read("NerdNostalgia-Scanner/Installa.cmd")
    ini = z.read("NerdNostalgia-Scanner/predefiniti.ini").decode()
    assert "api = " in ini and "password" not in ini
    assert client.get("/api/card-scanner/windows-kit").status_code == 401


# --- in vendita ovunque ----------------------------------------------------


def test_one_click_puts_the_card_on_site_and_cardtrader(client, admin_headers):
    carta = _carta_confermata(client, admin_headers)
    r = client.post(f"/api/card-scanner/cards/{carta['id']}/publish",
                    json={"site": True, "cardtrader": True}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json() == {"cardtrader": {"ok": True, "detail": None}, "site": {"ok": True, "detail": None}}
    c = client.get("/api/card-scanner/cards", headers=admin_headers).json()[0]
    assert c["site_status"] == "PUBLISHED" and c["cardtrader_product_id"] == 777


def test_a_channel_that_fails_does_not_stop_the_others(client, admin_headers, monkeypatch):
    from utils import ebay_client as eb
    monkeypatch.setattr(eb, "is_configured", lambda: True)
    carta = _carta_confermata(client, admin_headers)
    r = client.post(f"/api/card-scanner/cards/{carta['id']}/publish",
                    json={"site": True, "cardtrader": True, "ebay": True}, headers=admin_headers).json()
    assert r["cardtrader"]["ok"] and r["site"]["ok"]
    assert r["ebay"]["ok"] is False and "Impostazioni eBay" in r["ebay"]["detail"]


def test_republishing_does_not_duplicate_listings(client, admin_headers, mondo_finto):
    carta = _carta_confermata(client, admin_headers)
    corpo = {"site": True, "cardtrader": True}
    a = client.post(f"/api/card-scanner/cards/{carta['id']}/publish", json=corpo, headers=admin_headers)
    b = client.post(f"/api/card-scanner/cards/{carta['id']}/publish", json=corpo, headers=admin_headers)
    assert a.status_code == b.status_code == 200
    assert len(mondo_finto) == 1  # una sola inserzione CardTrader creata
    assert b.json()["cardtrader"]["ok"]  # la seconda volta la si aggiorna


def test_ebay_listing_has_a_link(client, admin_headers, db_session, monkeypatch):
    from utils import ebay_client as eb
    monkeypatch.setattr(eb, "is_sandbox", lambda: False)
    carta = _carta_confermata(client, admin_headers)
    card = db_session.get(PersonalCard, carta["id"])
    card.ebay_listing_id = "135792468"
    db_session.commit()
    c = client.get("/api/card-scanner/cards", headers=admin_headers).json()[0]
    assert c["ebay_url"] == "https://www.ebay.it/itm/135792468"


# --- prezzo eBay maggiorato -------------------------------------------------


def _ebay_finto(monkeypatch, client, admin_headers):
    """eBay collegato e configurato, ma finto: registra cosa gli si manda."""
    from utils import ebay_client as eb
    inviati = {}
    monkeypatch.setattr(eb, "is_configured", lambda: True)
    monkeypatch.setattr(eb, "put_inventory_item", lambda sku, body: inviati.setdefault("item", body))
    monkeypatch.setattr(eb, "get_offers", lambda sku: {"offers": []})
    monkeypatch.setattr(eb, "create_offer", lambda body: inviati.setdefault("offer", body) and {"offerId": "OF1"})
    monkeypatch.setattr(eb, "publish_offer", lambda oid: {"listingId": "LST1"})
    client.put("/api/settings/", json={"values": {
        "ebay_fulfillment_policy_id": "F", "ebay_payment_policy_id": "P",
        "ebay_return_policy_id": "R", "ebay_merchant_location_key": "L"}}, headers=admin_headers)
    return inviati


def _carta_con_foto_pubblica(client, admin_headers, db_session, prezzo="3.00"):
    carta = _carta_confermata(client, admin_headers)
    card = db_session.get(PersonalCard, carta["id"])
    card.images = ["https://api.example.test/static/scans/1/x.webp"]
    card.list_price = prezzo
    db_session.commit()
    return carta


def test_ebay_price_gets_the_ebay_markup(client, admin_headers, db_session, monkeypatch):
    from models.db import MarketplaceFee
    db_session.add(MarketplaceFee(marketplace="ebay", category_id=None, markup_percent=13, fixed_fee=0))
    db_session.commit()
    inviati = _ebay_finto(monkeypatch, client, admin_headers)
    carta = _carta_con_foto_pubblica(client, admin_headers, db_session)
    r = client.post(f"/api/card-scanner/cards/{carta['id']}/ebay", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["price_eur"] == 3.39
    assert inviati["offer"]["pricingSummary"]["price"]["value"] == "3.39"


def test_ebay_markup_falls_back_like_the_article_page(client, admin_headers, db_session, monkeypatch):
    """Nessuna commissione configurata: +11%, come la scheda articolo."""
    inviati = _ebay_finto(monkeypatch, client, admin_headers)
    carta = _carta_con_foto_pubblica(client, admin_headers, db_session, prezzo="10.00")
    client.post(f"/api/card-scanner/cards/{carta['id']}/ebay", headers=admin_headers)
    assert inviati["offer"]["pricingSummary"]["price"]["value"] == "11.10"


def test_category_markup_wins_over_the_default(db_session):
    from models.db import Category, MarketplaceFee
    from utils.card_listing import marketplace_markup
    carte = Category(name="Carte", slug="carte-t")
    db_session.add(carte); db_session.flush()
    poke = Category(name="Pokemon", slug="pokemon-t", parent_id=carte.id)
    db_session.add(poke); db_session.flush()
    db_session.add_all([
        MarketplaceFee(marketplace="ebay", category_id=None, markup_percent=11, fixed_fee=0),
        MarketplaceFee(marketplace="ebay", category_id=carte.id, markup_percent=14, fixed_fee=0),
    ])
    db_session.commit()
    assert marketplace_markup(db_session, "ebay", poke.id) == 14     # dal padre
    db_session.add(MarketplaceFee(marketplace="ebay", category_id=poke.id, markup_percent=9, fixed_fee=0))
    db_session.commit()
    assert marketplace_markup(db_session, "ebay", poke.id) == 9      # la sua
    assert marketplace_markup(db_session, "cardtrader", poke.id) == 0  # niente ripiego


def _errore_25098():
    from utils import ebay_client as eb
    return eb.EbayError("eBay 400 su /publish", 400, {"errors": [{
        "errorId": 25098, "message": "Questa inserzione viola le regole (Offerte di acquisto o "
        "vendita al di fuori di eBay). Impossibile applicare l'opzione Rimetti in vendita."}]})


def test_offer_blocked_by_ebay_is_replaced_with_a_clean_one(client, admin_headers, db_session, monkeypatch):
    """eBay ha tolto l'inserzione e non lascia ripubblicare quell'offerta:
    si cancella e si riparte da uno SKU nuovo."""
    from utils import ebay_client as eb
    _ebay_finto(monkeypatch, client, admin_headers)
    carta = _carta_con_foto_pubblica(client, admin_headers, db_session)
    card = db_session.get(PersonalCard, carta["id"])
    card.ebay_sku, card.ebay_offer_id = f"NN-PC-{card.id}", "VECCHIA"
    db_session.commit()

    cancellate, pubblicate, creati = [], [], []
    monkeypatch.setattr(eb, "update_offer", lambda oid, body: None)
    monkeypatch.setattr(eb, "delete_offer", lambda oid: cancellate.append(oid))
    monkeypatch.setattr(eb, "create_offer", lambda body: creati.append(body["sku"]) or {"offerId": "NUOVA"})

    def publish(oid):
        pubblicate.append(oid)
        if oid == "VECCHIA":
            raise _errore_25098()
        return {"listingId": "LST2"}
    monkeypatch.setattr(eb, "publish_offer", publish)

    r = client.post(f"/api/card-scanner/cards/{carta['id']}/ebay", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["action"] == "recreated"
    assert cancellate == ["VECCHIA"] and pubblicate == ["VECCHIA", "NUOVA"]
    assert creati == [f"NN-PC-{card.id}-r2"]
    db_session.refresh(card)
    assert (card.ebay_sku, card.ebay_offer_id, card.ebay_listing_id) == (f"NN-PC-{card.id}-r2", "NUOVA", "LST2")


def test_blocked_again_says_what_to_fix(client, admin_headers, db_session, monkeypatch):
    from utils import ebay_client as eb
    _ebay_finto(monkeypatch, client, admin_headers)
    carta = _carta_con_foto_pubblica(client, admin_headers, db_session)
    monkeypatch.setattr(eb, "delete_offer", lambda oid: None)
    def sempre_bloccata(oid):
        raise _errore_25098()
    monkeypatch.setattr(eb, "publish_offer", sempre_bloccata)
    r = client.post(f"/api/card-scanner/cards/{carta['id']}/ebay", headers=admin_headers)
    assert r.status_code == 400
    assert "footer eBay" in r.json()["detail"]


def test_discarded_scan_leaves_the_queue(client, admin_headers):
    scan = _carica(client, admin_headers).json()
    r = client.delete(f"/api/card-scanner/scans/{scan['id']}", headers=admin_headers)
    assert r.status_code == 204
    assert client.get("/api/card-scanner/scans", headers=admin_headers).json() == []


def test_only_admins(client):
    assert client.get("/api/card-scanner/status").status_code == 401
