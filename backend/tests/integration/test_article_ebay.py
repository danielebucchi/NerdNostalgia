"""Integration: articoli del sito su eBay (Inventory API), con le regole delle carte."""
import pytest

from models.db import Article, ArticleCondition, ArticleStatus, PersonalCard
from models.db.articles import EbayStatus


@pytest.fixture()
def ebay_finto(client, admin_headers, monkeypatch):
    """eBay collegato e configurato, che registra cosa gli si chiede."""
    from utils import ebay_client as eb
    chiamate = {"items": {}, "offers": [], "updated": [], "published": [], "withdrawn": []}
    monkeypatch.setattr(eb, "is_configured", lambda: True)
    monkeypatch.setattr(eb, "default_category_tree_id", lambda: "101")
    monkeypatch.setattr(eb, "category_suggestions", lambda tree, q: {"categorySuggestions": [
        {"category": {"categoryId": "139973", "categoryName": "Giochi"}}]})
    monkeypatch.setattr(eb, "item_aspects_for_category", lambda tree, cid: {"aspects": [
        {"localizedAspectName": "Piattaforma",
         "aspectConstraint": {"aspectRequired": True, "aspectMode": "SELECTION_ONLY"},
         "aspectValues": [{"localizedValue": "Nintendo 64"}, {"localizedValue": "Nintendo Game Boy"}]},
        {"localizedAspectName": "Marca",
         "aspectConstraint": {"aspectRequired": True, "aspectMode": "FREE_TEXT"}},
        {"localizedAspectName": "Titolo del gioco",
         "aspectConstraint": {"aspectRequired": True, "aspectMode": "FREE_TEXT"}},
        {"localizedAspectName": "Colore",
         "aspectConstraint": {"aspectRequired": False, "aspectMode": "FREE_TEXT"}},
    ]})
    monkeypatch.setattr(eb, "put_inventory_item", lambda sku, body: chiamate["items"].__setitem__(sku, body))
    monkeypatch.setattr(eb, "get_offers", lambda sku: {"offers": []})

    def crea_offerta(body):
        chiamate["offers"].append(body)
        return {"offerId": f"O{len(chiamate['offers'])}"}
    monkeypatch.setattr(eb, "create_offer", crea_offerta)
    monkeypatch.setattr(eb, "update_offer", lambda oid, body: chiamate["updated"].append((oid, body)))
    monkeypatch.setattr(eb, "publish_offer", lambda oid: chiamate["published"].append(oid) or {"listingId": "900"})
    monkeypatch.setattr(eb, "withdraw_offer", lambda oid: chiamate["withdrawn"].append(oid))
    client.put("/api/settings/", json={"values": {
        "ebay_fulfillment_policy_id": "F1", "ebay_payment_policy_id": "P1",
        "ebay_return_policy_id": "R1", "ebay_merchant_location_key": "casa",
        "marketplace_footer_ebay": "Spedizione Veloce\nAltri pezzi su www.nerdnostalgia.store",
    }}, headers=admin_headers)
    return chiamate


def _articolo(db_session, admin_user, **kw):
    dati = dict(
        user_id=admin_user.id, title="Super Mario 64 Nintendo 64 PAL",
        description="Cartuccia originale, testata.\nScrivimi su www.nerdnostalgia.store",
        price=20, condition=ArticleCondition.USED, status=ArticleStatus.PUBLISHED,
        images=["https://api.example.test/static/articles/1/a.webp"],
    )
    art = Article(**{**dati, **kw})
    db_session.add(art)
    db_session.commit()
    return art


def test_article_goes_on_ebay_with_the_cards_rules(client, admin_headers, db_session, admin_user, ebay_finto):
    art = _articolo(db_session, admin_user)
    r = client.post(f"/api/articles/{art.id}/ebay/publish", headers=admin_headers)
    assert r.status_code == 200, r.text
    esito = r.json()
    # 20 / 0,89 (ripiego 11%) = 22,47; +2 e +15% oltre i 15 = 25,59 → 26
    assert esito["price_eur"] == 26.0
    assert esito["url"].endswith("/itm/900") and esito["category_id"] == "139973"

    offerta = ebay_finto["offers"][0]
    assert offerta["pricingSummary"]["price"]["value"] == "26.00"
    assert offerta["categoryId"] == "139973" and offerta["sku"] == f"NN-ART-{art.id}"
    # Niente rimandi fuori da eBay, ne' dalla descrizione ne' dal footer
    assert "nerdnostalgia.store" not in offerta["listingDescription"]
    assert "Spedizione Veloce" in offerta["listingDescription"]

    item = ebay_finto["items"][f"NN-ART-{art.id}"]
    assert item["condition"] == "USED_EXCELLENT"
    aspetti = item["product"]["aspects"]
    assert aspetti["Piattaforma"] == ["Nintendo 64"]  # valore ammesso che compare nel titolo
    assert aspetti["Marca"] == ["Senza marca"]
    assert aspetti["Titolo del gioco"] == ["Non applicabile"]
    assert "Colore" not in aspetti  # facoltativo: non si inventa

    db_session.refresh(art)
    assert art.ebay_status == EbayStatus.LISTED and art.ebay_listing_id == "900"
    assert art.article_metadata["ebay_category_id"] == "139973"


def test_price_written_for_ebay_goes_to_the_euro_above(client, admin_headers, db_session, admin_user, ebay_finto):
    art = _articolo(db_session, admin_user, ebay_price=19.20)
    r = client.post(f"/api/articles/{art.id}/ebay/publish", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["price_eur"] == 20.0


def test_republishing_updates_the_same_listing(client, admin_headers, db_session, admin_user, ebay_finto):
    art = _articolo(db_session, admin_user)
    client.post(f"/api/articles/{art.id}/ebay/publish", headers=admin_headers)
    art.price = 50
    db_session.commit()
    r = client.post(f"/api/articles/{art.id}/ebay/publish", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["action"] == "updated"
    assert len(ebay_finto["offers"]) == 1 and ebay_finto["published"] == ["O1"]
    # 50 / 0,89 = 56,18; +2 e +15% oltre i 15 = 64,36 → 65
    assert ebay_finto["updated"][-1][1]["pricingSummary"]["price"]["value"] == "65.00"


def test_sold_on_the_site_is_withdrawn_from_ebay(client, admin_headers, db_session, admin_user, ebay_finto):
    art = _articolo(db_session, admin_user)
    client.post(f"/api/articles/{art.id}/ebay/publish", headers=admin_headers)
    r = client.post(f"/api/articles/{art.id}/sell", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert ebay_finto["withdrawn"] == ["O1"]
    db_session.refresh(art)
    assert art.ebay_listing_id is None and art.ebay_status == EbayStatus.NOT_LISTED


def test_deleting_the_article_withdraws_it_first(client, admin_headers, db_session, admin_user, ebay_finto):
    art = _articolo(db_session, admin_user)
    client.post(f"/api/articles/{art.id}/ebay/publish", headers=admin_headers)
    assert client.delete(f"/api/articles/{art.id}", headers=admin_headers).status_code == 204
    assert ebay_finto["withdrawn"] == ["O1"]


def test_collection_card_article_goes_through_the_scanner(client, admin_headers, db_session, admin_user, ebay_finto):
    art = _articolo(db_session, admin_user, title="Pokémon · Pikachu · Set Base 58/102 (IT, NM)")
    db_session.add(PersonalCard(name="Pikachu", quantity=1, article_id=art.id))
    db_session.commit()
    r = client.post(f"/api/articles/{art.id}/ebay/publish", headers=admin_headers)
    assert r.status_code == 400 and "scanner" in r.json()["detail"]
    anteprima = client.get(f"/api/articles/{art.id}/ebay/preview", headers=admin_headers).json()
    assert anteprima["collection_card"] and anteprima["collection_ebay_url"] is None

    # Su eBay con le varianti: il link e' quello dell'inserzione della carta
    carta = db_session.query(PersonalCard).filter(PersonalCard.article_id == art.id).one()
    carta.ebay_listing_id, carta.ebay_group_key = "800952062857", "NN-GRP-x"
    db_session.commit()
    anteprima = client.get(f"/api/articles/{art.id}/ebay/preview", headers=admin_headers).json()
    assert anteprima["collection_ebay_url"].endswith("/itm/800952062857")
    assert anteprima["collection_ebay_variations"] is True


def test_preview_shows_the_price_before_publishing(client, admin_headers, db_session, admin_user, ebay_finto):
    art = _articolo(db_session, admin_user)
    r = client.get(f"/api/articles/{art.id}/ebay/preview", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["price_eur"] == 26.0 and r.json()["listing_id"] is None


def test_price_chosen_before_publishing_wins_and_stays(client, admin_headers, db_session, admin_user, ebay_finto):
    art = _articolo(db_session, admin_user)
    assert client.get(f"/api/articles/{art.id}/ebay/preview", headers=admin_headers).json()["price_suggested"] == 26.0
    r = client.post(f"/api/articles/{art.id}/ebay/publish", json={"price": "21.50"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["price_eur"] == 22.0  # all'euro sopra
    # Aggiornando senza dire niente resta quello scelto; con null torna il suggerito
    assert client.post(f"/api/articles/{art.id}/ebay/publish", headers=admin_headers).json()["price_eur"] == 22.0
    r = client.post(f"/api/articles/{art.id}/ebay/publish", json={"price": None}, headers=admin_headers)
    assert r.json()["price_eur"] == 26.0


def test_saving_a_new_price_updates_the_ebay_listing(client, admin_headers, db_session, admin_user, ebay_finto):
    art = _articolo(db_session, admin_user, price=7)
    client.post(f"/api/articles/{art.id}/ebay/publish", headers=admin_headers)
    r = client.patch(f"/api/articles/{art.id}", json={"price": "10.00"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    # 10 / 0,89 = 11,24, +2 → 14
    assert ebay_finto["updated"][-1][1]["pricingSummary"]["price"]["value"] == "14.00"


def test_saving_without_changes_for_ebay_leaves_the_listing_alone(client, admin_headers, db_session, admin_user,
                                                                  ebay_finto):
    art = _articolo(db_session, admin_user)
    client.post(f"/api/articles/{art.id}/ebay/publish", headers=admin_headers)
    client.patch(f"/api/articles/{art.id}", json={"cost": "3.00"}, headers=admin_headers)
    assert ebay_finto["updated"] == []
