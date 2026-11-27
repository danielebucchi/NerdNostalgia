"""Guida prezzi: dati da CardTrader e TCGdex, pagine pubbliche, ricerca."""
from datetime import datetime

import pytest

from models.db import Article, ArticleCondition, ArticleStatus, PersonalCard, PriceGuideCard, PriceGuideSet
from utils import card_names_it, price_guide


@pytest.fixture
def fonti(monkeypatch):
    from utils import cardtrader_client as ct
    monkeypatch.setattr(ct, "is_configured", lambda: True)
    monkeypatch.setattr(ct, "expansions_cached", lambda: [
        {"id": 1472, "game_id": 5, "name": "Base Set"}, {"id": 9, "game_id": 5, "name": "Japanese Promo"},
        {"id": 7, "game_id": 1, "name": "Alpha"}])
    monkeypatch.setattr(card_names_it, "_set_pokemon", lambda nome: "base1" if nome == "Base Set" else None)
    tcg = {"tcgdex:en:base1": {"releaseDate": "1999-01-09", "cardCount": {"official": 102}, "logo": "https://l/base",
                               "serie": {"name": "Base"},
                               "cards": [{"localId": "4", "name": "Charizard", "image": "https://a/4"},
                                         {"localId": "2", "name": "Blastoise", "image": "https://a/2"}]},
           "tcgdex:it:base1": {"name": "Set Base", "serie": {"name": "Originale"},
                               "cards": [{"localId": "4", "name": "Charizard"}, {"localId": "2", "name": "Blastoise"}]}}
    monkeypatch.setattr(card_names_it, "_in_cache", lambda chiave, f: tcg.get(chiave))
    monkeypatch.setattr(ct, "blueprints_cached", lambda e: [
        {"id": 10, "name": "Base Set Booster", "fixed_properties": {}},
        {"id": 11, "name": "Charizard", "fixed_properties": {"collector_number": "004/102"}},
        {"id": 12, "name": "Blastoise", "fixed_properties": {"collector_number": "002/102"}}])
    monkeypatch.setattr(price_guide, "_prezzi", lambda e: {
        10: ({"normale": {"it": {"NM": 70000}}}, 3),
        11: ({"normale": {"it": {"NM": 55128, "SP": 40064, "PO": 13463}, "en": {"MP": 36867, "PO": 18564}},
              "1ed": {"it": {"PL": 90000}}}, 40),
        12: ({"normale": {"en": {"NM": 3951}}}, 25)})


def test_weekly_refresh_builds_sets_and_cards(db_session, fonti):
    esito = price_guide.aggiorna(db_session, pausa=0)
    assert esito["set"] == 1 and esito["carte"] == 2                                  # busta e set giapponese fuori
    s = db_session.query(PriceGuideSet).one()
    assert (s.slug, s.name_it, s.release_date, s.card_count, s.serie) == ("set-base", "Set Base", "1999-01-09", 102, "Originale")
    charizard = db_session.query(PriceGuideCard).filter_by(number="4").one()
    assert (charizard.slug, charizard.min_price_cents, charizard.offers) == ("4-charizard", 55128, 40)
    assert charizard.image_url == "https://a/4/high.webp"
    price_guide.aggiorna(db_session, pausa=0)                                           # di nuovo: niente doppioni
    assert db_session.query(PriceGuideCard).count() == 2


def test_public_pages_and_search(client, db_session, admin_user, fonti):
    price_guide.aggiorna(db_session, pausa=0)
    a = Article(user_id=admin_user.id, title="Charizard Set Base", price=150, condition=ArticleCondition.USED,
                status=ArticleStatus.PUBLISHED, quantity=1, images=["/static/x.webp"], published_at=datetime.utcnow())
    db_session.add(a)
    db_session.commit()
    db_session.add(PersonalCard(name="Charizard", article_id=a.id, cardtrader_blueprint_id=11))
    db_session.commit()

    sets = client.get("/api/price-guide/sets").json()
    assert sets[0]["slug"] == "set-base" and sets[0]["cards_priced"] == 2
    dettaglio = client.get("/api/price-guide/sets/set-base").json()
    assert [c["name"] for c in dettaglio["cards"]] == ["Blastoise", "Charizard"]
    carta = client.get("/api/price-guide/cards/set-base/4-charizard").json()
    assert carta["min_price"] == 551.28 and carta["available"]["id"] == a.id
    assert carta["prices"]["normale"]["it"]["PO"] == {"price": 134.63, "buy_offer": 80.7, "buy_bulk": None,
                                                      "buy_none": False}
    assert carta["prices"]["normale"]["en"]["MP"]["price"] == 368.67
    assert carta["prices"]["1ed"]["it"]["PL"]["buy_offer"] == 540.0
    assert client.get("/api/price-guide/cards/set-base/nessuna").status_code == 404
    trovate = client.get("/api/price-guide/search?q=charizard base").json()
    assert [c["name"] for c in trovate] == ["Charizard"]
    mappa = client.get("/api/price-guide/sitemap").json()
    assert {slug for _, slug in mappa["cards"]} == {"4-charizard", "2-blastoise"}


def test_buy_offer_rule(client, db_session, fonti):
    from helpers.setting import SettingHelper
    regola = price_guide.regola_offerta(db_session)
    o = lambda cent, data="1999-01-09", nome="Charizard": price_guide.offerta(cent, regola, data, nome)
    assert o(399) == {"tipo": "singola", "euro": 0.5}                 # 3,99 €: cifra fissa
    assert o(50) == {"tipo": "singola", "euro": 0.5}                  # 0,50 € esatti: singola
    assert o(12063) == {"tipo": "singola", "euro": 72.3}              # 60% di 120,63 → 72,30
    assert o(49) == {"tipo": "peso", "epoca": "vintage", "euro_kg": 7.0}
    assert o(20, "2010-05-01") == {"tipo": "peso", "epoca": "bordo giallo", "euro_kg": 5.0}
    assert o(20, "2024-01-26") == {"tipo": "peso", "epoca": "modern", "euro_kg": 3.0}
    assert o(10, "2010-05-01", "Fire Energy") == {"tipo": "no"}       # energie a peso: no
    assert o(10, "2010-05-01", "Double Colorless Energy (Holo)") == {"tipo": "no"}
    assert o(45, "1999-01-09", "Super Energy Removal")["tipo"] == "peso"   # Allenatore, non energia
    assert o(45, "1999-01-09", "Energy Search")["tipo"] == "peso"
    assert o(None) == {}
    price_guide.aggiorna(db_session, pausa=0)
    carta = client.get("/api/price-guide/cards/set-base/4-charizard").json()
    assert carta["buy_offer"] == 330.7 and carta["buy_bulk"] is None          # 60% del Near Mint italiano
    SettingHelper(db=db_session).upsert("buy_offer_percent", "50")
    assert client.get("/api/price-guide/search?q=blastoise").json()[0]["buy_offer"] == 19.7   # 50% di 39,51 (NM inglese)


def test_version_only_tells_real_variants_apart(db_session, fonti, monkeypatch):
    from utils import cardtrader_client as ct
    monkeypatch.setattr(ct, "blueprints_cached", lambda e: [
        {"id": 11, "name": "Charizard", "version": "Holo Rare | 4/102", "fixed_properties": {"collector_number": "004/102"}},
        {"id": 12, "name": "Blastoise", "version": "Holo Rare | 2/102", "fixed_properties": {"collector_number": "2"}},
        {"id": 13, "name": "Blastoise", "version": "Shadowless", "fixed_properties": {"collector_number": "2"}}])
    price_guide.aggiorna(db_session, pausa=0)
    slugs = {c.blueprint_id: (c.slug, c.name_en) for c in db_session.query(PriceGuideCard)}
    assert slugs[11] == ("4-charizard", "Charizard")
    assert slugs[13] == ("2-blastoise-shadowless", "Blastoise (Shadowless)")
    assert not price_guide.da_rifare(db_session)


def test_condition_table_from_offers():
    p = lambda cond, lingua, cent, **x: {"price": {"cents": cent, "currency": "EUR"},
                                          "properties_hash": {"condition": cond, "pokemon_language": lingua, **x}}
    tabella = price_guide.tabella_prezzi([
        p("Poor", "de", 12063),                       # tedesca: fuori
        p("Poor", "it", 13463), p("Played", "it", 15120), p("Near Mint", "it", 55128), p("Mint", "it", 90000),
        p("Slightly Played", "it", 60000),            # piu' cara della Near Mint: vale la Near Mint
        p("Near Mint", "it", 200000, first_edition=True), p("Played", "en", 9000, pokemon_reverse=True),
        p("Near Mint", "it", 100, signed=True),       # firmata: fuori
        p("Moderately Played", "en", 36867)])
    assert tabella == {"normale": {"it": {"NM": 55128, "SP": 55128, "PL": 15120, "PO": 13463}, "en": {"MP": 36867}},
                       "1ed": {"it": {"NM": 200000}}, "reverse": {"en": {"PL": 9000}}}
    assert price_guide.prezzo_in_evidenza(tabella) == 55128
    assert price_guide.prezzo_in_evidenza({"en": {"MP": 36867}}) == 36867          # formato di prima
    assert price_guide.prezzo_in_evidenza({"1ed": {"it": {"NM": 7}}}) == 7
