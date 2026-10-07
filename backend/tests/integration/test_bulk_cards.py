"""Caricamento massivo di carte.

CardTrader e' finto in tutti i test: pubblicare inserzioni vere mentre si
prova il codice vorrebbe dire mettere in vendita carte che non esistono.
"""
import pytest

from models.db import Article, ArticleStatus


@pytest.fixture(autouse=True)
def cardtrader_finto(monkeypatch):
    """Sostituisce le chiamate che escono verso CardTrader."""
    from utils import cardtrader_client as ct
    from utils import cardtrader_sync as cts

    monkeypatch.setattr(ct, "is_configured", lambda: True)

    inserzioni = []

    def finta_publish(db, article, **kw):
        inserzioni.append({"article_id": article.id, **kw})
        article.cardtrader_product_id = 9000 + len(inserzioni)
        db.commit()
        return {
            "action": "created",
            "product_id": article.cardtrader_product_id,
            "price_eur": 3.50,
            "quantity": kw.get("quantity") or 1,
            "price_meta": {"position": kw.get("price_position"), "total": 7},
        }

    monkeypatch.setattr(cts, "publish_article", finta_publish)
    return inserzioni


def _riga(**extra):
    base = {"blueprint_id": 123, "name": "Charizard VMAX", "number": "20",
            "collection": "Darkness Ablaze", "quantity": 1}
    base.update(extra)
    return base


# --- pubblicazione --------------------------------------------------------


def test_a_card_becomes_a_listing(client, admin_headers):
    r = client.post("/api/cards/bulk/publish",
                    json={"rows": [_riga()]}, headers=admin_headers)

    assert r.status_code == 200, r.text
    esito = r.json()[0]
    assert esito["ok"] is True
    assert esito["product_id"]
    assert esito["price_eur"] == 3.50


def test_the_card_stays_off_the_site(client, admin_headers):
    """Si caricano per vendere altrove: in catalogo non devono comparire."""
    r = client.post("/api/cards/bulk/publish",
                    json={"rows": [_riga()]}, headers=admin_headers)

    from main import app
    from utils.session import get_db
    db = next(app.dependency_overrides[get_db]())
    try:
        art = db.query(Article).filter(Article.id == r.json()[0]["article_id"]).first()
        assert art.status == ArticleStatus.DRAFT
    finally:
        db.close()


def test_the_price_comes_from_the_market_at_second_place(client, admin_headers, cardtrader_finto):
    """Il default e' il secondo prezzo piu' basso: e' la richiesta."""
    client.post("/api/cards/bulk/publish", json={"rows": [_riga()]}, headers=admin_headers)

    assert cardtrader_finto[0]["price_position"] == 2


def test_the_position_can_be_changed(client, admin_headers, cardtrader_finto):
    client.post("/api/cards/bulk/publish",
                json={"price_position": 5, "rows": [_riga()]}, headers=admin_headers)

    assert cardtrader_finto[0]["price_position"] == 5


def test_the_market_price_lands_on_the_article(client, admin_headers):
    """In inventario una carta a zero euro sarebbe solo confondente."""
    r = client.post("/api/cards/bulk/publish",
                    json={"rows": [_riga()]}, headers=admin_headers)

    from main import app
    from utils.session import get_db
    db = next(app.dependency_overrides[get_db]())
    try:
        art = db.query(Article).filter(Article.id == r.json()[0]["article_id"]).first()
        assert float(art.price) == 3.50
    finally:
        db.close()


def test_card_attributes_are_kept(client, admin_headers):
    r = client.post("/api/cards/bulk/publish", headers=admin_headers, json={"rows": [
        _riga(condition="Played", language="it", reverse=True, first_edition=True, quantity=4)
    ]})

    from main import app
    from utils.session import get_db
    db = next(app.dependency_overrides[get_db]())
    try:
        art = db.query(Article).filter(Article.id == r.json()[0]["article_id"]).first()
        assert art.card_condition == "Played"
        assert art.card_language == "it"
        assert art.card_reverse is True
        assert art.card_first_edition is True
        assert art.quantity == 4
    finally:
        db.close()


# --- una riga rotta non affonda il lotto ----------------------------------


def test_one_bad_row_does_not_sink_the_others(client, admin_headers, monkeypatch):
    """Cinquanta carte inserite a mano non si rifanno perche' la terza non
    si riesce a prezzare."""
    from utils import cardtrader_sync as cts

    chiamate = {"n": 0}
    originale = cts.publish_article

    def a_volte_fallisce(db, article, **kw):
        chiamate["n"] += 1
        if chiamate["n"] == 2:
            raise ValueError("Nessuna inserzione di riferimento per il prezzo")
        return originale(db, article, **kw)

    monkeypatch.setattr(cts, "publish_article", a_volte_fallisce)

    r = client.post("/api/cards/bulk/publish", headers=admin_headers, json={
        "rows": [_riga(blueprint_id=1), _riga(blueprint_id=2), _riga(blueprint_id=3)]
    })

    esiti = r.json()
    assert [e["ok"] for e in esiti] == [True, False, True]
    assert "prezzo" in esiti[1]["error"]


def test_a_failed_row_leaves_no_ghost_article(client, admin_headers, monkeypatch):
    """Un articolo in bozza senza inserzione non serve a niente, e in
    elenco sarebbe una riga da ripulire a mano."""
    from main import app
    from utils import cardtrader_sync as cts
    from utils.session import get_db

    monkeypatch.setattr(
        cts, "publish_article",
        lambda db, article, **kw: (_ for _ in ()).throw(ValueError("niente prezzo")),
    )

    db = next(app.dependency_overrides[get_db]())
    try:
        prima = db.query(Article).count()
    finally:
        db.close()

    client.post("/api/cards/bulk/publish", json={"rows": [_riga()]}, headers=admin_headers)

    db = next(app.dependency_overrides[get_db]())
    try:
        assert db.query(Article).count() == prima
    finally:
        db.close()


# --- limiti e accesso -----------------------------------------------------


def test_only_the_admin_can_load(client):
    r = client.post("/api/cards/bulk/publish", json={"rows": [_riga()]})
    assert r.status_code == 401


def test_there_is_a_ceiling_per_request(client, admin_headers):
    """Ogni riga costa due chiamate a CardTrader: un lotto enorme terrebbe
    la richiesta aperta per minuti senza dire a che punto e'."""
    from api.bulk_cards import MAX_RIGHE

    r = client.post("/api/cards/bulk/publish", headers=admin_headers,
                    json={"rows": [_riga() for _ in range(MAX_RIGHE + 1)]})

    assert r.status_code == 422


# --- CSV ------------------------------------------------------------------


@pytest.fixture
def blueprint_finto(monkeypatch):
    from utils import cardtrader_client as ct
    monkeypatch.setattr(ct, "blueprints_cached", lambda exp_id, **kw: [
        {"id": 111, "name": "Charizard VMAX", "collector_number": "020"},
        {"id": 222, "name": "Pikachu V", "collector_number": "043"},
    ])


def test_csv_is_read_with_semicolons(client, admin_headers, blueprint_finto):
    """Excel in italiano esporta col punto e virgola: un file cosi' deve
    entrare senza che nessuno lo riscriva."""
    csv = "nome;numero;quantita\nCharizard VMAX;20;3\n"

    r = client.post("/api/cards/bulk/parse-csv", headers=admin_headers,
                    json={"csv_text": csv, "expansion_id": 5})

    assert r.status_code == 200, r.text
    riga = r.json()[0]
    assert riga["name"] == "Charizard VMAX"
    assert riga["quantity"] == 3
    assert riga["candidates"][0]["id"] == 111


def test_csv_matches_by_number_inside_a_known_expansion(client, admin_headers, blueprint_finto):
    """Dentro un set il numero e' univoco: vale piu' del nome."""
    r = client.post("/api/cards/bulk/parse-csv", headers=admin_headers,
                    json={"csv_text": "numero\n43\n", "expansion_id": 5})

    assert r.json()[0]["candidates"][0]["id"] == 222


def test_csv_accepts_english_headers(client, admin_headers, blueprint_finto):
    r = client.post("/api/cards/bulk/parse-csv", headers=admin_headers,
                    json={"csv_text": "card,number,qty\nPikachu V,43,2\n", "expansion_id": 5})

    riga = r.json()[0]
    assert riga["name"] == "Pikachu V"
    assert riga["quantity"] == 2


def test_csv_reads_the_flags(client, admin_headers, blueprint_finto):
    r = client.post("/api/cards/bulk/parse-csv", headers=admin_headers, json={
        "csv_text": "nome;numero;reverse;prima_edizione;condizione;lingua\n"
                    "Pikachu V;43;si;x;Played;it\n",
        "expansion_id": 5,
    })

    riga = r.json()[0]
    assert riga["reverse"] is True
    assert riga["first_edition"] is True
    assert riga["condition"] == "Played"
    assert riga["language"] == "it"


def test_csv_without_a_usable_column_is_refused(client, admin_headers):
    r = client.post("/api/cards/bulk/parse-csv", headers=admin_headers,
                    json={"csv_text": "prezzo;note\n3;ciao\n"})

    assert r.status_code == 400
    assert "nome" in r.json()["detail"]


def test_csv_does_not_publish_anything(client, admin_headers, blueprint_finto, cardtrader_finto):
    """La risoluzione propone, non decide: una carta sbagliata messa in
    vendita la si scopre quando qualcuno l'ha comprata."""
    client.post("/api/cards/bulk/parse-csv", headers=admin_headers,
                json={"csv_text": "nome;numero\nCharizard VMAX;20\n", "expansion_id": 5})

    assert cardtrader_finto == []
