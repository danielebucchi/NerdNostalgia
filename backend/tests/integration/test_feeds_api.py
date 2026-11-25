"""Feed per Google Merchant Center: solo cio' che si puo' comprare adesso."""
import xml.etree.ElementTree as ET

from models.db import Article, ArticleCondition, ArticleStatus

G = "{http://base.google.com/ns/1.0}"


def _art(db, admin_user, titolo, **kw):
    base = dict(user_id=admin_user.id, title=titolo, price=12.3, condition=ArticleCondition.USED,
                status=ArticleStatus.PUBLISHED, quantity=1, images=["/static/articles/1/a.webp"])
    a = Article(**{**base, **kw})
    db.add(a)
    db.commit()
    return a


def _voci(client):
    r = client.get("/api/feeds/google.xml")
    assert r.status_code == 200 and "xml" in r.headers["content-type"]
    return {i.find(f"{G}id").text: i for i in ET.fromstring(r.text).iter("item")}


def test_only_items_that_can_be_bought_now(client, db_session, admin_user):
    ok = _art(db_session, admin_user, "Charizard Set Base 4/102")
    _art(db_session, admin_user, "Bozza", status=ArticleStatus.DRAFT)
    _art(db_session, admin_user, "Venduto", status=ArticleStatus.SOLD)
    _art(db_session, admin_user, "Senza foto", images=[])
    _art(db_session, admin_user, "Esaurito", quantity=0)
    voci = _voci(client)
    assert list(voci) == [f"nn-{ok.id}"]


def test_fields_google_needs(client, db_session, admin_user):
    a = _art(db_session, admin_user, "Super Mario 64 & co", condition=ArticleCondition.NEW,
             description="Cartuccia   originale\n con scatola", brand="Nintendo",
             images=["/static/articles/1/a.webp", "https://cdn.example.test/b.webp"])
    v = _voci(client)[f"nn-{a.id}"]
    assert v.find(f"{G}title").text == "Super Mario 64 & co"
    assert v.find(f"{G}description").text == "Cartuccia originale con scatola"
    assert v.find(f"{G}price").text == "12.30 EUR"
    assert v.find(f"{G}condition").text == "new"
    assert v.find(f"{G}availability").text == "in_stock"
    assert v.find(f"{G}brand").text == "Nintendo"
    assert v.find(f"{G}link").text.endswith(f"/articles/{a.id}")
    assert v.find(f"{G}image_link").text.startswith("http") and v.find(f"{G}image_link").text.endswith("/static/articles/1/a.webp")
    assert v.find(f"{G}additional_image_link").text == "https://cdn.example.test/b.webp"
