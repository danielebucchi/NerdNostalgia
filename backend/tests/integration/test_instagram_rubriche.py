"""Rubriche Instagram: una al giorno, ripiego se manca materiale, LISTA in DM."""
from datetime import datetime, timedelta

import pytest

from models.db import (Article, ArticleCondition, ArticleStatus, CardPriceHistory, InstagramMedia,
                       InstagramReply, PersonalCard)
from utils import instagram, instagram_reel, instagram_rubriche as rub


@pytest.fixture
def ig(monkeypatch, db_session):
    from helpers.setting import SettingHelper
    monkeypatch.setenv("INSTAGRAM_USER_ID", "1789")
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "tok")
    SettingHelper(db=db_session).upsert("instagram_enabled", "true")
    class Chiamate(list):
        commenti: list

    chiamate = Chiamate()
    commenti = []

    def finta(metodo, percorso, token, **parametri):
        chiamate.append((metodo, percorso, parametri))
        if percorso.endswith("/comments"):
            return {"data": list(commenti)}
        if metodo == "GET":
            return {"status_code": "FINISHED"}
        return {"id": f"m{len(chiamate)}"}
    monkeypatch.setattr(instagram, "_chiama", finta)
    monkeypatch.setattr(instagram_reel, "monta", lambda slide, seme: b"mp4")
    monkeypatch.setattr(instagram_reel, "salva", lambda contenuto, nome, estensione="mp4": f"https://x/{nome}.{estensione}")
    chiamate.commenti = commenti
    return chiamate


def _art(db, admin_user, titolo, prezzo, giorni_fa=30, carta=None):
    a = Article(user_id=admin_user.id, title=titolo, price=prezzo, condition=ArticleCondition.USED,
                status=ArticleStatus.PUBLISHED, quantity=1, images=["/static/x.webp"],
                published_at=datetime.utcnow() - timedelta(days=giorni_fa))
    db.add(a)
    db.commit()
    if carta:
        db.add(PersonalCard(name=titolo, article_id=a.id, **carta))
        db.commit()
    return a


def test_no_material_no_rubric_that_day(db_session, admin_user, ig):
    for i in range(4):
        _art(db_session, admin_user, f"Economica {i}", 2 + i)
    assert rub.prepara(db_session, giorno=0) is None              # lunedi': nessun nuovo arrivo
    assert rub.pubblica(db_session, giorno=0) is None and ig == []
    nome, articoli, testo, (tipo, media) = rub.prepara(db_session, giorno=2)
    assert nome == "sotto5" and tipo == "carosello" and len(media) == len(articoli) + 2   # copertina e finale
    assert "Commenta LISTA" in testo


def test_new_arrivals_reel_and_price_quiz(db_session, admin_user, ig):
    for i in range(3):
        _art(db_session, admin_user, f"Nuovo {i}", 10 + i, giorni_fa=2)
    assert rub.prepara(db_session, giorno=0)[0] == "nuovi"
    _art(db_session, admin_user, "Charizard", 40, carta={"cardtrader_price": 52.5})
    nome, articoli, testo, (tipo, media) = rub.prepara(db_session, giorno=1)
    assert nome == "quiz" and tipo == "reel" and articoli[0].title == "Charizard"


def test_cards_that_went_up(db_session, admin_user, ig):
    assert rub.carte_salite(db_session) is None
    for i, (prima, dopo) in enumerate([(2, 5), (10, 11), (3, 9), (1, 4)]):
        a = _art(db_session, admin_user, f"Carta {i}", dopo, carta={"collection": "Base Set"})
        carta = db_session.query(PersonalCard).filter_by(article_id=a.id).one()
        db_session.add(CardPriceHistory(card_id=carta.id, value=prima, recorded_at=datetime.now() - timedelta(days=7)))
        db_session.add(CardPriceHistory(card_id=carta.id, value=dopo, recorded_at=datetime.now()))
    db_session.commit()
    nome, articoli, testo, _ = rub.carte_salite(db_session)
    assert [a.title for a in articoli] == ["Carta 3", "Carta 2", "Carta 0", "Carta 1"]  # per crescita %
    assert "da 2,00 € a 5,00 € (+150%)" in testo


def test_rare_one_is_not_repeated(db_session, admin_user, ig):
    _art(db_session, admin_user, "Costosa", 200)
    _art(db_session, admin_user, "Meno costosa", 80)
    assert rub.pubblica(db_session, giorno=6)["rubrica"] == "rara"
    assert len([p for _, _, p in ig if p.get("media_type") == "STORIES"]) == 1       # la sua Storia
    assert db_session.query(InstagramMedia).filter_by(rubrica="rara").one().article_ids
    assert rub.prepara(db_session, giorno=6)[1][0].title == "Meno costosa"


def test_rubric_once_a_day_in_its_slot(db_session, admin_user, ig, monkeypatch):
    from utils import instagram_stats
    _art(db_session, admin_user, "Costosa", 200)
    monkeypatch.setattr(instagram_stats, "slot_di_oggi", lambda db: "18:30")
    originale = rub.prepara
    monkeypatch.setattr(rub, "prepara", lambda db, giorno=None: originale(db, 6))   # domenica: la rara
    assert rub.slot_rubrica(db_session) == "12:30"
    assert rub.rubrica_del_giorno(db_session, "18:30") is None
    assert rub.rubrica_del_giorno(db_session, "12:30") is not None
    assert rub.rubrica_del_giorno(db_session, "12:30") is None


def test_comment_lista_gets_the_links_in_private_once(db_session, admin_user, ig):
    a = _art(db_session, admin_user, "Pikachu", 3)
    db_session.add(InstagramMedia(media_id="p1", kind="post", published_at=datetime.now() - timedelta(hours=3),
                                  article_ids=str(a.id), hashtags=""))
    db_session.commit()
    ig.commenti += [{"id": "c1", "text": "Lista please!", "username": "ash"},
                    {"id": "c2", "text": "bellissima", "username": "misty"}]
    assert rub.rispondi_ai_commenti(db_session) == 1
    dm = [p for m, path, p in ig if path.endswith("/messages")][0]
    assert '"comment_id": "c1"' in dm["recipient"] and f"/articles/{a.id}" in dm["message"]
    assert any(path == "c1/replies" for _, path, _ in ig)
    assert rub.rispondi_ai_commenti(db_session) == 0                                  # gia' risposto
    assert db_session.get(InstagramReply, "c1") is not None


def test_gift_ideas_follow_the_italian_occasions():
    from datetime import date
    attese = {date(2026, 11, 26): "per Natale", date(2026, 12, 24): "per Natale",
              date(2026, 12, 27): "per la Befana", date(2027, 1, 6): "per la Befana",
              date(2027, 1, 20): "per chi ama collezionare", date(2027, 2, 10): "per San Valentino",
              date(2027, 3, 19): "per la Festa del papà", date(2027, 5, 9): "per la Festa della mamma",
              date(2027, 5, 10): "per chi ama collezionare", date(2027, 9, 1): "per il ritorno a scuola",
              date(2027, 10, 20): "per Halloween"}
    for giorno, testo in attese.items():
        assert rub.ricorrenza(giorno) == testo, giorno
