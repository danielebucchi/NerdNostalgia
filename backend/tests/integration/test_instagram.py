"""Instagram: immagini nel formato giusto, carosello e Storie una volta sola."""
import io
from datetime import datetime, timedelta

import pytest
from PIL import Image

from models.db import Article, ArticleCondition, ArticleStatus
from utils import instagram


@pytest.fixture
def ig(monkeypatch, db_session):
    """Instagram configurato e acceso, Graph API finta."""
    from helpers.setting import SettingHelper
    monkeypatch.setenv("INSTAGRAM_USER_ID", "1789")
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "tok")
    SettingHelper(db=db_session).upsert("instagram_enabled", "true")
    chiamate = []

    def finta(metodo, percorso, token, **parametri):
        chiamate.append((metodo, percorso, parametri))
        if metodo == "GET":
            return {"status_code": "FINISHED"}
        return {"id": f"m{len(chiamate)}"}
    monkeypatch.setattr(instagram, "_chiama", finta)
    return chiamate


def _foto(articolo_id):
    from utils.storage import UPLOADS_DIR
    cartella = UPLOADS_DIR / "articles" / str(articolo_id)
    cartella.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (496, 687), (200, 50, 50)).save(cartella / "a.webp", "WEBP")
    return f"/static/articles/{articolo_id}/a.webp"


def _articolo(db, admin_user, titolo="Charizard Set Base", prezzo=12.3, giorni_fa=0):
    a = Article(user_id=admin_user.id, title=titolo, price=prezzo, condition=ArticleCondition.USED,
                status=ArticleStatus.PUBLISHED, quantity=1,
                published_at=datetime.utcnow() - timedelta(days=giorni_fa))
    db.add(a)
    db.commit()
    a.images = [_foto(a.id)]
    db.commit()
    return a


def test_images_have_instagram_proportions(client, db_session, admin_user):
    a = _articolo(db_session, admin_user, "Un titolo molto lungo " * 6)
    for formato, misure in (("post", (1080, 1350)), ("storia", (1080, 1920))):
        r = client.get(f"/api/social/instagram/{a.id}/{formato}.jpg")
        assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
        assert Image.open(io.BytesIO(r.content)).size == misure
    a.status = ArticleStatus.DRAFT
    db_session.commit()
    assert client.get(f"/api/social/instagram/{a.id}/post.jpg").status_code == 404


def test_daily_carousel_most_expensive_first_and_only_once(db_session, admin_user, ig):
    for i in range(12):
        _articolo(db_session, admin_user, f"Carta {i}", prezzo=1 + i)
    _articolo(db_session, admin_user, "Vecchia", prezzo=99, giorni_fa=5)
    esito = instagram.pubblica_carosello(db_session)
    assert len(esito["articoli"]) == instagram.MAX_CAROSELLO
    carosello = [p for m, path, p in ig if p.get("media_type") == "CAROUSEL"][0]
    assert carosello["caption"].index("Carta 11") < carosello["caption"].index("Carta 2")
    assert "Vecchia" not in carosello["caption"] and "t.me/NerdNostalgia" in carosello["caption"]
    assert len(carosello["children"].split(",")) == 10
    # Il giorno dopo restano le due piu' economiche: un post singolo.
    ig.clear()
    esito = instagram.pubblica_carosello(db_session)
    assert len(esito["articoli"]) == 2 and esito["ripescato"] is False


def test_single_article_is_a_plain_post(db_session, admin_user, ig):
    _articolo(db_session, admin_user)
    instagram.pubblica_carosello(db_session)
    assert not any(p.get("media_type") == "CAROUSEL" for _, _, p in ig)
    assert any(path.endswith("media_publish") for _, path, _ in ig)


def test_stories_only_above_threshold_once_and_capped(db_session, admin_user, ig):
    _articolo(db_session, admin_user, "Economica", prezzo=5)
    for i in range(12):
        _articolo(db_session, admin_user, f"Cara {i}", prezzo=25)
    assert len(instagram.pubblica_storie(db_session)) == instagram.MAX_STORIE_GIORNO
    assert instagram.pubblica_storie(db_session) == []           # tetto del giorno
    storie = [p for _, _, p in ig if p.get("media_type") == "STORIES"]
    assert all("/storia.jpg" in p["image_url"] for p in storie)


def test_off_or_not_configured_does_nothing(db_session, admin_user, ig, monkeypatch):
    from helpers.setting import SettingHelper
    _articolo(db_session, admin_user, prezzo=50)
    SettingHelper(db=db_session).upsert("instagram_enabled", "false")
    assert instagram.pubblica_carosello(db_session) is None and instagram.pubblica_storie(db_session) == []
    SettingHelper(db=db_session).upsert("instagram_enabled", "true")
    monkeypatch.delenv("INSTAGRAM_USER_ID")
    assert instagram.pubblica_carosello(db_session) is None
    assert ig == []


def test_status_shows_what_will_go_out(client, admin_headers, db_session, admin_user, ig):
    _articolo(db_session, admin_user, prezzo=30)
    st = client.get("/api/social/instagram/status", headers=admin_headers).json()
    assert st["enabled"] is True and len(st["next_carousel"]) == 1 and len(st["next_stories"]) == 1
    assert st["next_carousel"][0]["image"].split("?")[0].endswith("/post.jpg")
    assert client.get("/api/social/instagram/status").status_code == 401


def test_token_refresh_only_for_instagram_login(db_session, monkeypatch):
    monkeypatch.setenv("INSTAGRAM_USER_ID", "1789")
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "tok")
    chiamate = []
    monkeypatch.setattr(instagram.requests, "get", lambda *a, **k: chiamate.append(a) or None)
    monkeypatch.delenv("INSTAGRAM_GRAPH_URL", raising=False)
    assert instagram.rinnova_token(db_session) is False and chiamate == []   # utente di sistema: non scade


def test_no_news_posts_one_older_article_going_back(db_session, admin_user, ig):
    antico = _articolo(db_session, admin_user, "Antico", giorni_fa=40)
    vecchio = _articolo(db_session, admin_user, "Vecchio", giorni_fa=10)
    venduto = _articolo(db_session, admin_user, "Venduto", giorni_fa=5)
    venduto.status = ArticleStatus.SOLD
    db_session.commit()
    primo = instagram.pubblica_carosello(db_session)
    assert primo["articoli"] == [vecchio.id] and primo["ripescato"] is True
    assert "ancora disponibile" in [p for _, _, p in ig if "caption" in p][0]["caption"]
    assert instagram.pubblica_carosello(db_session)["articoli"] == [antico.id]
    assert instagram.pubblica_carosello(db_session) is None          # catalogo tutto passato


def test_every_article_of_the_post_gets_a_story_once(db_session, admin_user, ig):
    from helpers.setting import SettingHelper
    SettingHelper(db=db_session).upsert("instagram_story_min_price", "100")    # nessuna per soglia
    gia = _articolo(db_session, admin_user, "Gia' con Storia", prezzo=150)
    instagram.pubblica_storie(db_session)
    for i in range(3):
        _articolo(db_session, admin_user, f"Carta {i}", prezzo=2)
    ig.clear()
    instagram.pubblica_carosello(db_session)
    storie = [p["image_url"] for _, _, p in ig if p.get("media_type") == "STORIES"]
    assert len(storie) == 3 and not any(f"/{gia.id}/" in u for u in storie)
