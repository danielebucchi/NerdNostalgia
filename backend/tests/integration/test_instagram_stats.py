"""Statistiche Instagram: orario e hashtag scelti dai dati, report, Reel del mese."""
from datetime import date, datetime, timedelta

import pytest

from models.db import Article, ArticleCondition, ArticleStatus, InstagramMedia
from utils import instagram, instagram_reel, instagram_stats


@pytest.fixture
def ig(monkeypatch, db_session):
    from helpers.setting import SettingHelper
    monkeypatch.setenv("INSTAGRAM_USER_ID", "1789")
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "tok")
    SettingHelper(db=db_session).upsert("instagram_enabled", "true")
    chiamate = []

    def finta(metodo, percorso, token, **parametri):
        chiamate.append((metodo, percorso, parametri))
        if percorso.endswith("/insights"):
            return {"data": [{"name": "reach", "values": [{"value": 321}]},
                             {"name": "saved", "values": [{"value": 4}]}]}
        if percorso.endswith("/media") and metodo == "GET":
            return {"data": [{"id": "vecchio1", "caption": "Ciao #Pokemon #retro", "media_type": "IMAGE",
                              "timestamp": "2026-11-01T11:35:00+0000"}]}
        if metodo == "GET":
            return {"status_code": "FINISHED"}
        return {"id": f"m{len(chiamate)}"}
    monkeypatch.setattr(instagram, "_chiama", finta)
    return chiamate


def _post(db, media_id, ora, reach, hashtags="", slot=None, giorni_fa=1):
    quando = (datetime.now() - timedelta(days=giorni_fa)).replace(hour=int(ora[:2]), minute=int(ora[3:]))
    db.add(InstagramMedia(media_id=media_id, kind="post", published_at=quando, slot=slot,
                          reach=reach, hashtags=hashtags))
    db.commit()


def test_history_and_insights_are_collected(db_session, ig):
    assert instagram_stats.importa_storico(db_session) == 1
    vecchio = db_session.get(InstagramMedia, "vecchio1")
    assert vecchio.hashtags == "#pokemon #retro" and vecchio.published_at.hour == 12   # 11:35 UTC = 12:35 a Roma
    assert instagram_stats.importa_storico(db_session) == 0                            # gia' importato
    vecchio.published_at = datetime.now() - timedelta(days=2)
    db_session.commit()
    assert instagram_stats.aggiorna(db_session) == 1
    assert vecchio.reach == 321 and vecchio.saved == 4


def test_slot_tries_every_hour_then_keeps_the_best(db_session):
    assert instagram_stats.scegli_slot(db_session, date(2026, 12, 1)) == "18:30"     # nessun dato
    for i in range(3):
        _post(db_session, f"a{i}", "12:30", 100, giorni_fa=i + 1)
    assert instagram_stats.scegli_slot(db_session, date(2026, 12, 1)) == "18:30"     # da provare
    for i in range(3):
        _post(db_session, f"b{i}", "18:30", 50, giorni_fa=i + 1)
        _post(db_session, f"c{i}", "21:00", 300, giorni_fa=i + 1)
    scelte = [instagram_stats.scegli_slot(db_session, date(2026, 12, 1) + timedelta(days=d)) for d in range(40)]
    assert scelte.count("21:00") > 25 and set(scelte) <= set(instagram_stats.SLOT)


def test_daily_post_only_in_the_chosen_slot_and_once(db_session, admin_user, ig, monkeypatch):
    a = Article(user_id=admin_user.id, title="Pikachu", price=3, condition=ArticleCondition.USED,
                status=ArticleStatus.PUBLISHED, quantity=1, images=["/static/x.webp"], published_at=datetime.utcnow())
    db_session.add(a)
    db_session.commit()
    monkeypatch.setattr(instagram_stats, "slot_di_oggi", lambda db: "21:00")
    monkeypatch.setattr(instagram, "_storie", lambda db, token, articoli: [])
    assert instagram.post_del_giorno(db_session, "18:30") is None
    assert instagram.post_del_giorno(db_session, "21:00")["articoli"] == [a.id]
    assert instagram.post_del_giorno(db_session, "21:00") is None                    # gia' uscito oggi
    registrato = db_session.query(InstagramMedia).filter_by(kind="post").one()
    assert registrato.slot == "21:00"


def test_hashtags_keep_the_ones_that_reach_more_people(db_session):
    _post(db_session, "x1", "18:30", 900, "#pokemontcg #nerdnostalgia")
    _post(db_session, "x2", "18:30", 10, "#pokemon #nerdnostalgia")
    scelti = instagram_stats.hashtag_per(db_session, []).split()
    assert scelti[0] == "#nerdnostalgia" and len(scelti) <= instagram_stats.MAX_HASHTAG
    assert "#vintage" in scelti or "#collezionismo" in scelti                        # da scoprire


def test_weekly_report(db_session):
    assert instagram_stats.report(db_session) is None
    _post(db_session, "r1", "21:00", 250, "#retro")
    testo = instagram_stats.report(db_session)["text"]
    assert "250" in testo and "21:00" in testo


def test_monthly_reel_of_sold_items(db_session, admin_user, ig, monkeypatch):
    monkeypatch.setattr(instagram_reel, "video", lambda articoli, anno, mese: b"mp4")
    monkeypatch.setattr(instagram_reel, "_salva", lambda contenuto, anno, mese: "https://x/reel.mp4")
    assert instagram_reel.pubblica(db_session, 2026, 11) is None                     # niente venduti
    for i, giorno in enumerate((3, 20)):
        db_session.add(Article(user_id=admin_user.id, title=f"Venduto {i}", price=5 + i, quantity=1,
                               condition=ArticleCondition.USED, status=ArticleStatus.SOLD,
                               images=["/static/x.webp"], sold_at=datetime(2026, 11, giorno)))
    db_session.add(Article(user_id=admin_user.id, title="Di ottobre", price=9, quantity=1,
                           condition=ArticleCondition.USED, status=ArticleStatus.SOLD,
                           images=["/static/x.webp"], sold_at=datetime(2026, 10, 30)))
    db_session.commit()
    esito = instagram_reel.pubblica(db_session, 2026, 11)
    assert esito["articoli"] == 2
    reel = [p for _, _, p in ig if p.get("media_type") == "REELS"][0]
    assert reel["video_url"] == "https://x/reel.mp4" and "novembre: 2 pezzi" in reel["caption"]
    assert instagram_reel.pubblica(db_session, 2026, 11) is None                     # uno al mese
    assert db_session.query(InstagramMedia).filter_by(kind="reel").count() == 1


def test_chiptune_is_a_wav_of_the_right_length():
    import io
    import wave
    from utils import chiptune
    with wave.open(io.BytesIO(chiptune.musica(3, seme=1))) as w:
        assert w.getnframes() == 3 * chiptune.FREQ
    assert chiptune.musica(2, seme=1) != chiptune.musica(2, seme=2)


def test_admin_stats_endpoint(client, admin_headers, db_session):
    _post(db_session, "s1", "12:30", 80, "#retro")
    r = client.get("/api/social/instagram/stats", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["reach_by_slot"]["12:30"] == {"posts": 1, "avg_reach": 80}
    assert client.get("/api/social/instagram/stats").status_code == 401
