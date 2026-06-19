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
