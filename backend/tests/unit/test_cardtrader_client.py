"""Unit: filtri prezzo (condizione/lingua/reverse/1a ed.) + build properties."""
from utils import cardtrader_client as ct


def _p(cents, **props):
    return {"price": {"cents": cents}, "properties_hash": props}


def test_match_filters_condition_language():
    props = {"condition": "Near Mint", "pokemon_language": "it", "pokemon_reverse": False}
    assert ct._match_filters(props, condition="Near Mint", language="it") is True
    assert ct._match_filters(props, condition="Mint") is False
    assert ct._match_filters(props, language="en") is False


def test_match_filters_reverse_and_first_edition_defaults():
    # chiave reverse/first_edition assente = trattata come False
    props = {"condition": "Near Mint", "pokemon_language": "it"}
    assert ct._match_filters(props, reverse=False, first_edition=False) is True
    assert ct._match_filters(props, reverse=True) is False
    assert ct._match_filters({"first_edition": True}, first_edition=True) is True


def test_suggested_price_filtered(monkeypatch):
    listings = [
        _p(11, condition="Near Mint", pokemon_language="it", pokemon_reverse=False),
        _p(14, condition="Near Mint", pokemon_language="en", pokemon_reverse=False),
        _p(20, condition="Near Mint", pokemon_language="it", pokemon_reverse=False),
        _p(30, condition="Mint", pokemon_language="it", pokemon_reverse=False),
        _p(40, condition="Near Mint", pokemon_language="it", pokemon_reverse=True),
    ]
    monkeypatch.setattr(ct, "marketplace_products", lambda bid: listings)
    # Solo NM + it + no reverse: [11, 20] → 4° clampato all'ultimo = 20
    res = ct.suggested_price_cents(
        1, 4, condition="Near Mint", language="it", reverse=False, first_edition=False
    )
    assert res["cents"] == 20
    assert res["total"] == 2
    assert res["filtered"] is True


def test_suggested_price_unfiltered(monkeypatch):
    listings = [_p(11), _p(12), _p(13), _p(14), _p(15)]
    monkeypatch.setattr(ct, "marketplace_products", lambda bid: listings)
    res = ct.suggested_price_cents(1, 4)
    assert res["cents"] == 14  # 4° piu' basso
    assert res["filtered"] is False


def test_suggested_price_excludes_graded(monkeypatch):
    listings = [
        {"price": {"cents": 500}, "graded": True, "properties_hash": {"condition": "Near Mint"}},
        _p(10), _p(12), _p(15), _p(18),
    ]
    monkeypatch.setattr(ct, "marketplace_products", lambda bid: listings)
    res = ct.suggested_price_cents(1, 4)
    # lo slab da 500 e' escluso → 4° = 18, non 15
    assert res["cents"] == 18
    assert res["total"] == 4


def test_create_product_includes_description(monkeypatch):
    monkeypatch.setattr(ct, "blueprint_editable_properties", lambda bid: [{"name": "condition"}])
    captured = {}

    def fake_request(method, path, *, params=None, json=None):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = json
        return {"id": 1}

    monkeypatch.setattr(ct, "_request", fake_request)
    ct.create_product(1, 1.0, description="Reverse holo\n\nAsk For Photos")
    assert captured["json"]["description"] == "Reverse holo\n\nAsk For Photos"

    # description vuota → chiave assente nel body
    ct.create_product(1, 1.0, description="   ")
    assert "description" not in captured["json"]


def test_build_product_properties(monkeypatch):
    editable = [
        {"name": "condition"},
        {"name": "pokemon_language"},
        {"name": "pokemon_reverse"},
    ]
    monkeypatch.setattr(ct, "blueprint_editable_properties", lambda bid: editable)
    props = ct.build_product_properties(
        1, condition="Mint", language="it", reverse=True, first_edition=True
    )
    assert props == {"condition": "Mint", "pokemon_language": "it", "pokemon_reverse": True}
    # first_edition non e' fra le editable → non inviata
    assert "first_edition" not in props
