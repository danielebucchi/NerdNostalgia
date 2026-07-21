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


def _bp(number, name, bp_id):
    return {"id": bp_id, "name": name, "fixed_properties": {"collector_number": number}}


def test_resolve_in_expansion_unique(monkeypatch):
    """Numero univoco dentro l'espansione → blueprint deterministico."""
    monkeypatch.setattr(
        cts.ct, "blueprints_cached",
        lambda eid: [_bp("004/165", "Charmander", 111), _bp("025/165", "Pikachu", 222)],
    )
    assert cts.resolve_in_expansion(3403, "4", "Charmander") == 111
    assert cts.resolve_in_expansion(3403, "025", None) == 222


def test_resolve_in_expansion_number_disambiguated_by_name(monkeypatch):
    """Stesso numero su più blueprint → disambigua col nome carta."""
    monkeypatch.setattr(
        cts.ct, "blueprints_cached",
        lambda eid: [_bp("4", "Charizard", 1), _bp("4", "Blastoise", 2)],
    )
    assert cts.resolve_in_expansion(3403, "4", "Charizard") == 1


def test_resolve_in_expansion_no_match(monkeypatch):
    monkeypatch.setattr(cts.ct, "blueprints_cached", lambda eid: [_bp("1", "Bulbasaur", 9)])
    assert cts.resolve_in_expansion(3403, "999", "X") is None
    assert cts.resolve_in_expansion(None, "1", "X") is None


def test_auto_publish_noop_without_jwt(monkeypatch):
    """Senza JWT configurato l'auto-push non fa nulla e non solleva."""
    monkeypatch.setattr(cts.ct, "is_configured", lambda: False)
    art = SimpleNamespace(category=_cat("carte"), cardtrader_blueprint_id=123, id=1)
    res = cts.auto_publish_if_card(None, art)
    assert res["status"] == "skipped"


def test_auto_publish_noop_card_without_blueprint(monkeypatch):
    """Carta senza blueprint e non risolvibile → unmatched, nessun push."""
    monkeypatch.setattr(cts.ct, "is_configured", lambda: True)
    monkeypatch.setattr(cts, "resolve_single", lambda *a, **k: None)
    monkeypatch.setattr(cts, "resolve_in_expansion", lambda *a, **k: None)
    art = SimpleNamespace(
        category=_cat("carte"), cardtrader_blueprint_id=None, id=2,
        card_collection=None, card_number=None, title="X",
    )
    res = cts.auto_publish_if_card(None, art)
    assert res["status"] == "unmatched"
