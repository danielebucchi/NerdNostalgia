"""Unit: rilevamento carta + guard auto-push CardTrader."""
from types import SimpleNamespace

from utils import cardtrader_sync as cts


def _cat(slug, parent=None):
    return SimpleNamespace(
        slug=slug,
        parent_id=None if parent is None else parent.id,
        parent=parent,
        id=hash(slug) % 1000,
    )


def test_is_card_top_level():
    carte = _cat("carte")
    art = SimpleNamespace(category=carte)
    assert cts.is_card_article(art) is True


def test_is_card_subcategory():
    carte = _cat("carte")
    pokemon = _cat("pokemon", parent=carte)
    art = SimpleNamespace(category=pokemon)
    assert cts.is_card_article(art) is True


def test_not_card_other_category():
    videogiochi = _cat("videogiochi")
    art = SimpleNamespace(category=videogiochi)
    assert cts.is_card_article(art) is False


def test_not_card_no_category():
    assert cts.is_card_article(SimpleNamespace(category=None)) is False


def test_auto_publish_noop_without_jwt(monkeypatch):
    """Senza JWT configurato l'auto-push non fa nulla e non solleva."""
    monkeypatch.setattr(cts.ct, "is_configured", lambda: False)
    art = SimpleNamespace(category=_cat("carte"), cardtrader_blueprint_id=123, id=1)
    assert cts.auto_publish_if_card(None, art) is None


def test_auto_publish_noop_card_without_blueprint(monkeypatch):
    monkeypatch.setattr(cts.ct, "is_configured", lambda: True)
    art = SimpleNamespace(category=_cat("carte"), cardtrader_blueprint_id=None, id=2)
    assert cts.auto_publish_if_card(None, art) is None
