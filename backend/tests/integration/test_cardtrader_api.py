"""Integration: ricerca carte CardTrader dalla scheda articolo."""


def _blueprints(monkeypatch):
    from utils import cardtrader_client as ct
    monkeypatch.setattr(ct, "is_configured", lambda: True)
    monkeypatch.setattr(ct, "blueprints", lambda expansion_id: [
        {"id": 1, "name": "Base Set Booster", "fixed_properties": {}},
        {"id": 2, "name": "Venusaur", "fixed_properties": {"collector_number": "015"}},
        {"id": 3, "name": "Gyarados", "fixed_properties": {"collector_number": "006"}},
        {"id": 4, "name": "Machop", "fixed_properties": {"collector_number": "052"}},
    ])


def test_blueprint_search_finds_the_card_by_printed_number(client, admin_headers, monkeypatch):
    """Il numero sta in fixed_properties, e "15" e' il "015" stampato."""
    _blueprints(monkeypatch)
    r = client.get("/api/cardtrader/blueprints?expansion_id=1472&search=15", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert [b["name"] for b in r.json()] == ["Venusaur"]
    r = client.get("/api/cardtrader/blueprints?expansion_id=1472&search=15/102", headers=admin_headers)
    assert [b["name"] for b in r.json()] == ["Venusaur"]


def test_blueprint_search_by_name_still_works(client, admin_headers, monkeypatch):
    _blueprints(monkeypatch)
    r = client.get("/api/cardtrader/blueprints?expansion_id=1472&search=gyara", headers=admin_headers)
    assert [b["name"] for b in r.json()] == ["Gyarados"]


def test_suggested_price_defaults_to_the_second_lowest(client, admin_headers, monkeypatch):
    from utils import cardtrader_client as ct
    monkeypatch.setattr(ct, "is_configured", lambda: True)
    chiesto = {}

    def prezzo(bp, pos, **kw):
        chiesto["pos"] = pos
        return {"cents": 900, "position": pos, "total": 5, "all_cents": [], "filtered": True}

    monkeypatch.setattr(ct, "suggested_price_cents", prezzo)
    r = client.get("/api/cardtrader/suggested-price?blueprint_id=2", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert chiesto["pos"] == 2


def _articolo_su_cardtrader(db_session, admin_user, **kw):
    from models.db import Article, ArticleCondition, ArticleStatus
    art = Article(user_id=admin_user.id, title="Venusaur 15 base set", price=50,
                  condition=ArticleCondition.USED, status=ArticleStatus.PUBLISHED,
                  cardtrader_blueprint_id=2, cardtrader_product_id=555, **kw)
    db_session.add(art)
    db_session.commit()
    return art


def test_collection_card_is_not_published_twice_from_the_article(client, admin_headers, db_session, admin_user,
                                                                   monkeypatch):
    from models.db import PersonalCard
    from utils import cardtrader_client as ct
    monkeypatch.setattr(ct, "is_configured", lambda: True)
    art = _articolo_su_cardtrader(db_session, admin_user)
    art.cardtrader_product_id = None
    db_session.add(PersonalCard(name="Venusaur", quantity=1, article_id=art.id))
    db_session.commit()
    r = client.post(f"/api/cardtrader/publish/{art.id}", json={"condition": "Poor", "price_eur": 50},
                    headers=admin_headers)
    assert r.status_code == 400 and "collezione" in r.json()["detail"]
    assert client.get(f"/api/articles/{art.id}", headers=admin_headers).json()["collection_card_id"]


def test_archiving_or_deleting_withdraws_from_cardtrader(client, admin_headers, db_session, admin_user, monkeypatch):
    from utils import cardtrader_client as ct
    ritirati = []
    monkeypatch.setattr(ct, "delete_product", lambda pid: ritirati.append(pid))
    a = _articolo_su_cardtrader(db_session, admin_user)
    assert client.post(f"/api/articles/{a.id}/archive", headers=admin_headers).status_code == 200
    b = _articolo_su_cardtrader(db_session, admin_user)
    b.cardtrader_product_id = 556
    db_session.commit()
    assert client.delete(f"/api/articles/{b.id}", headers=admin_headers).status_code == 204
    assert ritirati == [555, 556]
