"""Canale Telegram dei nuovi arrivi: un annuncio per articolo, mai di piu'."""
import pytest

from models.db import Article, ArticleCondition, ArticleStatus
from utils import category_alerts, telegram_channel


@pytest.fixture
def canale(monkeypatch):
    inviati = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@nerdnostalgia")
    monkeypatch.setattr(telegram_channel, "_invia", inviati.append)

    class Subito:  # il thread parte e finisce subito, per vedere l'invio nel test
        def __init__(self, target, args, daemon=None):
            self.t, self.a = target, args

        def start(self):
            self.t(*self.a)
    monkeypatch.setattr(telegram_channel.threading, "Thread", Subito)
    telegram_channel._inviati.clear()
    return inviati


def _articolo(db, admin_user, titolo="Charizard <Set Base>"):
    a = Article(user_id=admin_user.id, title=titolo, price=12.3, condition=ArticleCondition.USED,
                status=ArticleStatus.PUBLISHED, quantity=1)
    db.add(a)
    db.commit()
    return a


def test_new_article_is_announced_once(db_session, admin_user, canale):
    a = _articolo(db_session, admin_user)
    category_alerts.notify_new_article(db_session, a)
    category_alerts.notify_new_article(db_session, a)      # ripubblicato: niente doppione
    assert len(canale) == 1
    assert "Charizard &lt;Set Base&gt;" in canale[0] and "12,30 €" in canale[0]
    assert f"/articles/{a.id}" in canale[0]


def test_without_configuration_nothing_is_sent(db_session, admin_user, canale, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN")
    category_alerts.notify_new_article(db_session, _articolo(db_session, admin_user))
    assert canale == []


def test_at_most_twenty_an_hour(db_session, admin_user, canale):
    for i in range(25):
        telegram_channel.annuncia(db_session, _articolo(db_session, admin_user, f"Carta {i}"))
    assert len(canale) == telegram_channel.MAX_ORA


def test_topic_of_a_group_with_topics(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@nerdnostalgia")
    monkeypatch.delenv("TELEGRAM_TOPIC_ID", raising=False)
    assert "message_thread_id" not in telegram_channel.payload("ciao")
    monkeypatch.setenv("TELEGRAM_TOPIC_ID", "42")
    assert telegram_channel.payload("ciao")["message_thread_id"] == 42


def test_no_news_today_two_older_articles_a_day(db_session, admin_user, canale):
    from datetime import datetime, timedelta
    vecchio = _articolo(db_session, admin_user, "Vecchio")
    vecchio.published_at = datetime.utcnow() - timedelta(days=30)
    recente = _articolo(db_session, admin_user, "Recente")
    recente.published_at = datetime.utcnow() - timedelta(days=5)
    db_session.commit()
    assert telegram_channel.ripesca(db_session) == recente.id
    assert telegram_channel.ripesca(db_session) == vecchio.id
    assert "Ancora disponibile" in canale[0] and "Recente" in canale[0]
    assert telegram_channel.ripesca(db_session) is None              # tutti postati da poco
    # Postato 70 giorni fa: si puo' riproporre.
    meta = dict(vecchio.article_metadata)
    meta["telegram_posted_at"] = (datetime.now() - timedelta(days=70)).isoformat(timespec="seconds")
    vecchio.article_metadata = meta
    db_session.commit()
    assert telegram_channel.ripesca(db_session) == vecchio.id


def test_no_fishing_on_days_with_new_arrivals(db_session, admin_user, canale):
    vecchio = _articolo(db_session, admin_user, "Vecchio")
    nuovo = _articolo(db_session, admin_user, "Nuovo")
    category_alerts.notify_new_article(db_session, nuovo)
    assert telegram_channel.ripesca(db_session) is None
    assert len(canale) == 1 and vecchio.id
