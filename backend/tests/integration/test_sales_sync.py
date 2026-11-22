"""Vendite su CardTrader/eBay: la carta si ritira dagli altri canali.

Senza, una carta venduta su eBay restava in vendita sul sito e su
CardTrader e poteva vendersi due volte."""
import pytest

from models.db import Article, ArticleStatus, PersonalCard
from tests.integration.test_card_scanner_api import _carta_confermata, mondo_finto  # noqa: F401


@pytest.fixture
def canali_finti(monkeypatch):
    from utils import cardtrader_client as ct, ebay_client as eb, email as em
    stato = {"ordini": [], "offerte": {}, "ritirate_ct": [], "ritirate_ebay": [], "email": []}
    monkeypatch.setattr(ct, "is_configured", lambda: True)
    monkeypatch.setattr(eb, "is_configured", lambda: True)
    monkeypatch.setattr(ct, "_request", lambda m, path, **kw: stato["ordini"] if kw["params"]["page"] == 1 else [])
    monkeypatch.setattr(ct, "delete_product", lambda pid: stato["ritirate_ct"].append(pid))
    monkeypatch.setattr(eb, "get_offers", lambda sku: {"offers": stato["offerte"].get(sku, [])})
    monkeypatch.setattr(eb, "withdraw_offer", lambda oid: stato["ritirate_ebay"].append(oid))
    monkeypatch.setattr(em, "send_email", lambda **kw: stato["email"].append(kw) or True)
    return stato


def _in_vendita_ovunque(client, admin_headers, db_session):
    carta = _carta_confermata(client, admin_headers)
    art_id = client.post(f"/api/card-scanner/cards/{carta['id']}/site", headers=admin_headers).json()["article_id"]
    client.post(f"/api/card-scanner/cards/{carta['id']}/cardtrader", headers=admin_headers)
    card = db_session.get(PersonalCard, carta["id"])
    card.ebay_sku, card.ebay_offer_id, card.ebay_listing_id = f"NN-PC-{card.id}", "O1", "800000000001"
    db_session.commit()
    return card, art_id


def test_sold_on_ebay_leaves_the_site_and_cardtrader(client, admin_headers, db_session, canali_finti):
    card, art_id = _in_vendita_ovunque(client, admin_headers, db_session)
    canali_finti["offerte"][card.ebay_sku] = [{"listing": {"soldQuantity": 1},
                                              "pricingSummary": {"price": {"value": "5.90"}}}]
    r = client.post("/api/card-scanner/sync-sales", headers=admin_headers)
    assert r.status_code == 200, r.text
    db_session.refresh(card)
    assert (card.status, card.sold_platform, float(card.sale_price)) == ("SOLD", "ebay", 5.90)
    assert canali_finti["ritirate_ct"] == [777]
    assert canali_finti["ritirate_ebay"] == []  # venduta li': niente da ritirare
    assert db_session.get(Article, art_id).status == ArticleStatus.ARCHIVED
    assert "venduto su ebay" in canali_finti["email"][0]["text_body"]


def test_sold_on_cardtrader_leaves_ebay_and_the_site(client, admin_headers, db_session, canali_finti):
    card, art_id = _in_vendita_ovunque(client, admin_headers, db_session)
    canali_finti["ordini"] = [{"state": "paid", "order_items": [
        {"product_id": 777, "quantity": 1, "seller_price": {"cents": 450, "currency": "EUR"}}]}]
    client.post("/api/card-scanner/sync-sales", headers=admin_headers)
    db_session.refresh(card)
    assert (card.status, card.sold_platform, float(card.sale_price)) == ("SOLD", "cardtrader", 4.50)
    assert canali_finti["ritirate_ebay"] == ["O1"]
    assert db_session.get(Article, art_id).status == ArticleStatus.ARCHIVED


def test_cancelled_order_and_unsold_offer_change_nothing(client, admin_headers, db_session, canali_finti):
    card, _ = _in_vendita_ovunque(client, admin_headers, db_session)
    canali_finti["ordini"] = [{"state": "canceled", "order_items": [{"product_id": 777, "quantity": 1}]}]
    canali_finti["offerte"][card.ebay_sku] = [{"listing": {"soldQuantity": 0}}]
    esito = client.post("/api/card-scanner/sync-sales", headers=admin_headers).json()
    assert esito["vendute"] == []
    db_session.refresh(card)
    assert card.status == "IN_STOCK" and canali_finti["email"] == []


def test_one_marketplace_down_does_not_stop_the_other(client, admin_headers, db_session, canali_finti, monkeypatch):
    from utils import cardtrader_client as ct

    def giu(*a, **kw):
        raise ct.CardTraderError("CardTrader 503", 503)
    monkeypatch.setattr(ct, "_request", giu)
    card, _ = _in_vendita_ovunque(client, admin_headers, db_session)
    canali_finti["offerte"][card.ebay_sku] = [{"listing": {"soldQuantity": 1}}]
    esito = client.post("/api/card-scanner/sync-sales", headers=admin_headers).json()
    assert "cardtrader" in esito["errori"] and len(esito["vendute"]) == 1


# --- articoli del sito (non carte della collezione) ----------------------


def _articolo_su_ebay_e_cardtrader(db_session, admin_user, **kw):
    from models.db import ArticleCondition
    from models.db.articles import EbayStatus, VintedStatus
    art = Article(user_id=admin_user.id, title="Magneton set base 9 holo poor pokemon", price=10,
                  condition=ArticleCondition.USED, status=ArticleStatus.PUBLISHED,
                  ebay_sku="NN-ART-1", ebay_offer_id="OA1", ebay_listing_id="800952341340",
                  ebay_status=EbayStatus.LISTED, cardtrader_blueprint_id=5, cardtrader_product_id=888,
                  vinted_status=VintedStatus.LISTED, **kw)
    db_session.add(art)
    db_session.commit()
    return art


def test_article_sold_on_ebay_is_sold_on_the_site_and_leaves_cardtrader(
        client, admin_headers, db_session, admin_user, canali_finti):
    from models.db.articles import EbayStatus
    art = _articolo_su_ebay_e_cardtrader(db_session, admin_user)
    canali_finti["offerte"]["NN-ART-1"] = [{"listing": {"soldQuantity": 1},
                                           "pricingSummary": {"price": {"value": "14.00"}}}]
    r = client.post("/api/card-scanner/sync-sales", headers=admin_headers)
    assert r.status_code == 200, r.text
    db_session.refresh(art)
    assert art.status == ArticleStatus.SOLD and art.ebay_status == EbayStatus.SOLD
    assert canali_finti["ritirate_ct"] == [888] and canali_finti["ritirate_ebay"] == []
    testo = canali_finti["email"][0]["text_body"]
    assert "Magneton" in testo and "venduto su ebay a 14.00" in testo and "vinted" in testo


def test_article_sold_on_cardtrader_leaves_ebay(client, admin_headers, db_session, admin_user, canali_finti):
    art = _articolo_su_ebay_e_cardtrader(db_session, admin_user)
    canali_finti["ordini"] = [{"state": "paid", "order_items": [
        {"product_id": 888, "quantity": 1, "seller_price": {"cents": 900, "currency": "EUR"}}]}]
    client.post("/api/card-scanner/sync-sales", headers=admin_headers)
    db_session.refresh(art)
    assert art.status == ArticleStatus.SOLD
    assert canali_finti["ritirate_ebay"] == ["OA1"]


def test_unsold_article_stays_on_sale(client, admin_headers, db_session, admin_user, canali_finti):
    art = _articolo_su_ebay_e_cardtrader(db_session, admin_user)
    canali_finti["offerte"]["NN-ART-1"] = [{"listing": {"soldQuantity": 0}}]
    client.post("/api/card-scanner/sync-sales", headers=admin_headers)
    db_session.refresh(art)
    assert art.status == ArticleStatus.PUBLISHED and canali_finti["email"] == []
