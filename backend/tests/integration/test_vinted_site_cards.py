"""Carte nate sul sito e copiate su Vinted: la sync le segue.

Prima la sync conosceva solo gli articoli nati da Vinted (vinted_item_id):
una carta del sito messa su Vinted veniva vista come "carta nuova" e
saltata, e se si vendeva li' restava in vendita sul sito, su CardTrader e
su eBay."""
from models.db import Article, ArticleStatus, PersonalCard, VintedStatus
from tests.integration.test_card_scanner_api import _carta_confermata, mondo_finto  # noqa: F401


def _carta_sul_sito(client, admin_headers, db_session):
    carta = _carta_confermata(client, admin_headers)
    art_id = client.post(f"/api/card-scanner/cards/{carta['id']}/site", headers=admin_headers).json()["article_id"]
    client.post(f"/api/card-scanner/cards/{carta['id']}/cardtrader", headers=admin_headers)
    return db_session.get(PersonalCard, carta["id"]), art_id


def _annuncio(item_id, titolo, stato=None):
    return {"item_id": item_id, "title": titolo, "price": 3.5,
            "url": f"https://www.vinted.it/items/{item_id}-carta", "status": stato,
            "catalog_branch_title": "Carte collezionabili", "brand": "Pokémon"}


def _sync(client, admin_headers, *annunci):
    r = client.post("/api/vinted/import", headers=admin_headers,
                    json={"items": list(annunci), "triggered_by": "remote"})
    assert r.status_code == 200, r.text


def test_linked_by_url_and_sold_on_vinted_leaves_everywhere(client, admin_headers, db_session, mondo_finto):
    card, art_id = _carta_sul_sito(client, admin_headers, db_session)
    r = client.patch(f"/api/articles/{art_id}/vinted", headers=admin_headers, json={
        "vinted_status": "LISTED", "vinted_url": "https://www.vinted.it/items/5123456789-spearow"})
    assert r.status_code == 200, r.text
    assert db_session.get(Article, art_id).vinted_item_id == 5123456789

    _sync(client, admin_headers, _annuncio(5123456789, "qualsiasi titolo", stato="sold"))
    db_session.expire_all()
    art = db_session.get(Article, art_id)
    assert (art.status, art.vinted_status) == (ArticleStatus.SOLD, VintedStatus.SOLD)
    card = db_session.get(PersonalCard, card.id)
    assert (card.status, card.sold_platform, float(card.sale_price)) == ("SOLD", "vinted", 3.5)
    assert card.cardtrader_product_id is None      # ritirata da CardTrader


def test_same_vinted_listing_cannot_link_two_articles(client, admin_headers, db_session, mondo_finto):
    _, a = _carta_sul_sito(client, admin_headers, db_session)
    _, b = _carta_sul_sito(client, admin_headers, db_session)
    url = "https://www.vinted.it/items/77-carta"
    assert client.patch(f"/api/articles/{a}/vinted", headers=admin_headers,
                        json={"vinted_status": "LISTED", "vinted_url": url}).status_code == 200
    r = client.patch(f"/api/articles/{b}/vinted", headers=admin_headers,
                     json={"vinted_status": "LISTED", "vinted_url": url})
    assert r.status_code == 409 and f"#{a}" in r.json()["detail"]


def test_copied_card_is_linked_by_its_vinted_title(client, admin_headers, db_session, mondo_finto):
    """Senza incollare il link: il titolo e' quello che genera il pannello."""
    from utils.card_listing import vinted_title
    card, art_id = _carta_sul_sito(client, admin_headers, db_session)
    _sync(client, admin_headers, _annuncio(888, vinted_title(card).upper()))
    db_session.expire_all()
    assert db_session.get(Article, art_id).vinted_item_id == 888


def test_two_identical_cards_are_not_guessed(client, admin_headers, db_session, mondo_finto):
    from utils.card_listing import vinted_title
    card, a = _carta_sul_sito(client, admin_headers, db_session)
    _, b = _carta_sul_sito(client, admin_headers, db_session)
    _sync(client, admin_headers, _annuncio(889, vinted_title(card)))
    db_session.expire_all()
    assert db_session.get(Article, a).vinted_item_id is None
    assert db_session.get(Article, b).vinted_item_id is None


def test_removed_from_vinted_the_card_stays_on_the_site(client, admin_headers, db_session, mondo_finto):
    from datetime import datetime
    from models.db import VintedSyncLog
    _, art_id = _carta_sul_sito(client, admin_headers, db_session)
    client.patch(f"/api/articles/{art_id}/vinted", headers=admin_headers, json={
        "vinted_status": "LISTED", "vinted_url": "https://www.vinted.it/items/4242-carta"})
    art = db_session.get(Article, art_id)
    art.vinted_synced_at = datetime(2026, 1, 1)
    db_session.add(VintedSyncLog(started_at=datetime(2026, 9, 10), finished_at=datetime(2026, 9, 10),
                                 triggered_by="remote", items_fetched=40))
    db_session.commit()
    r = client.post("/api/vinted/reconcile", headers=admin_headers, json={"missing_item_ids": [4242]})
    assert r.status_code == 200, r.text
    db_session.expire_all()
    art = db_session.get(Article, art_id)
    assert art.status == ArticleStatus.PUBLISHED and art.vinted_item_id is None
