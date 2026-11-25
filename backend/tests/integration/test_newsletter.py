"""Newsletter dei nuovi arrivi: solo a chi ha il consenso, solo se accesa,
una volta a settimana, sempre con il link per revocare."""
from datetime import datetime, timedelta

import pytest

from models.db import Article, ArticleCondition, ArticleStatus, User
from utils import newsletter


@pytest.fixture
def posta(monkeypatch):
    from utils import email as em
    inviate = []
    monkeypatch.setattr(em, "send_email", lambda **kw: inviate.append(kw) or True)
    return inviate


def _cliente(db, email, consenso):
    u = User(username=email, email=email, hashed_password="x", role="USER",
             is_active=True, is_verified=True, marketing_consent=consenso)
    db.add(u)
    db.commit()
    return u


def _novita(db, admin_user, titolo="Charizard", giorni_fa=1):
    a = Article(user_id=admin_user.id, title=titolo, price=12.3, condition=ArticleCondition.USED,
                status=ArticleStatus.PUBLISHED, quantity=1, images=["/static/a.webp"],
                published_at=datetime.utcnow() - timedelta(days=giorni_fa))
    db.add(a)
    db.commit()
    return a


def test_only_customers_who_said_yes_and_with_the_revoke_link(db_session, admin_user, posta):
    _cliente(db_session, "si@example.test", True)
    _cliente(db_session, "no@example.test", False)
    _novita(db_session, admin_user)
    _novita(db_session, admin_user, "Vecchio", giorni_fa=20)
    esito = newsletter.invia(db_session)
    assert esito == {"inviate": 1, "articoli": 1}
    assert [m["to"] for m in posta] == ["si@example.test"]
    assert "Charizard" in posta[0]["html_body"] and "Vecchio" not in posta[0]["html_body"]
    assert "/disiscriviti?t=" in posta[0]["text_body"]


def test_weekly_run_only_if_enabled_and_once_a_week(db_session, admin_user, posta):
    from helpers.setting import SettingHelper
    _cliente(db_session, "si@example.test", True)
    _novita(db_session, admin_user)
    assert newsletter.run_settimanale(db_session) is None and posta == []   # spenta di default
    SettingHelper(db=db_session).upsert("newsletter_enabled", "true")
    assert newsletter.run_settimanale(db_session)["inviate"] == 1
    assert newsletter.run_settimanale(db_session) is None                    # gia' partita
    assert len(posta) == 1


def test_no_new_arrivals_no_email(db_session, posta):
    _cliente(db_session, "si@example.test", True)
    assert newsletter.invia(db_session)["inviate"] == 0 and posta == []


def test_preview_goes_only_to_the_admin(client, admin_headers, db_session, admin_user, posta):
    _cliente(db_session, "si@example.test", True)
    _novita(db_session, admin_user)
    r = client.post("/api/newsletter/preview", headers=admin_headers)
    assert r.status_code == 200 and r.json()["anteprima"] is True
    assert len(posta) == 1 and posta[0]["to"] != "si@example.test"
    st = client.get("/api/newsletter/status", headers=admin_headers).json()
    assert st == {"enabled": False, "last_sent": None, "recipients": 1, "new_articles": 1}
