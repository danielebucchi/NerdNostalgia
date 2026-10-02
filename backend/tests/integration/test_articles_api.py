"""Test su GET /api/articles/."""
import pytest

from models.db import Article, ArticleStatus, ArticleCondition


@pytest.fixture()
def seed_articles(db_session, admin_user):
    """Crea 3 articoli: 1 published, 1 draft, 1 sold."""
    items = [
        Article(
            user_id=admin_user.id,
            title="Nintendo 64 perfetto",
            description="console anni 90",
            price=120,
            condition=ArticleCondition.USED,
            status=ArticleStatus.PUBLISHED,
        ),
        Article(
            user_id=admin_user.id,
            title="Game Boy Color giallo",
            description="con scatola",
            price=80,
            condition=ArticleCondition.USED,
            status=ArticleStatus.DRAFT,
        ),
        Article(
            user_id=admin_user.id,
            title="PS2 slim nera",
            description="venduta",
            price=60,
            condition=ArticleCondition.USED,
            status=ArticleStatus.SOLD,
        ),
    ]
    for a in items:
        db_session.add(a)
    db_session.commit()
    for a in items:
        db_session.refresh(a)
    return items


def test_list_all(client, seed_articles):
    r = client.get("/api/articles/")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3


def test_list_filter_status_published(client, seed_articles):
    r = client.get("/api/articles/?status=PUBLISHED")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "PUBLISHED"
    assert "Nintendo" in items[0]["title"]


def test_list_filter_min_max_price(client, seed_articles):
    r = client.get("/api/articles/?min_price=70&max_price=100")
    assert r.status_code == 200
    items = r.json()["items"]
    titles = [i["title"] for i in items]
    assert "Game Boy Color giallo" in titles
    assert "Nintendo 64 perfetto" not in titles  # >100
    assert "PS2 slim nera" not in titles         # <70


def test_search_by_title(client, seed_articles):
    r = client.get("/api/articles/?search=nintendo")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert "Nintendo" in items[0]["title"]


def test_search_by_description(client, seed_articles):
    """ilike funziona anche su description (case-insensitive)."""
    r = client.get("/api/articles/?search=scatola")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert "Game Boy" in items[0]["title"]


def test_get_by_id(client, seed_articles):
    article_id = seed_articles[0].id
    r = client.get(f"/api/articles/{article_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == article_id
    assert "Nintendo" in body["title"]


def test_get_by_id_not_found(client):
    r = client.get("/api/articles/99999")
    assert r.status_code == 404


def test_list_pagination(client, seed_articles):
    r = client.get("/api/articles/?skip=0&limit=2")
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["skip"] == 0
    assert body["limit"] == 2


# ───────────────── Rincaro di listino ─────────────────

def _make(client, admin_headers, admin_user, title, price, status="PUBLISHED"):
    return client.post(
        "/api/articles/", headers=admin_headers,
        json={
            "user_id": admin_user.id, "title": title, "price": price,
            "currency": "EUR", "condition": "USED", "status": status,
            "quantity": 1,
        },
    ).json()


def test_bulk_markup_is_a_preview_by_default(client, admin_headers, admin_user):
    """Riscrivere i prezzi di tutto il catalogo non deve poter partire per
    sbaglio: senza dry_run=false non si tocca niente."""
    art = _make(client, admin_headers, admin_user, "Carta", 10)

    r = client.post(
        "/api/articles/bulk-markup", headers=admin_headers,
        json={"percent": 3.5},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["dry_run"] is True
    assert any(c["id"] == art["id"] and c["new_price"] == 10.35
               for c in body["changes"])
    # Il prezzo in DB non e' cambiato
    assert float(client.get(f"/api/articles/{art['id']}").json()["price"]) == 10.0


def test_bulk_markup_applies_when_asked(client, admin_headers, admin_user):
    art = _make(client, admin_headers, admin_user, "Console", 100)

    client.post(
        "/api/articles/bulk-markup", headers=admin_headers,
        json={"percent": 3.5, "dry_run": False},
    )
    assert float(client.get(f"/api/articles/{art['id']}").json()["price"]) == 103.5


def test_bulk_markup_leaves_sold_articles_alone(
    client, admin_headers, admin_user,
):
    """Il prezzo di un pezzo venduto e' storia, non listino."""
    sold = _make(client, admin_headers, admin_user, "Venduto", 50, status="SOLD")

    client.post(
        "/api/articles/bulk-markup", headers=admin_headers,
        json={"percent": 3.5, "dry_run": False},
    )
    assert float(client.get(f"/api/articles/{sold['id']}").json()["price"]) == 50.0


def test_bulk_markup_requires_admin(client):
    r = client.post("/api/articles/bulk-markup", json={"percent": 3.5})
    assert r.status_code == 401

