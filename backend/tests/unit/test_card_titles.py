"""Unit: titoli e ricerche delle carte della collezione."""
from models.db import PersonalCard
from utils.card_listing import ebay_title
from utils.card_pricing import ebay_sold_url


def _carta(**kw):
    base = dict(id=1, name="Charizard", printed_code="004/102", collection="Base Set",
                language="it", condition="Near Mint", game_id=5, reverse=False, first_edition=False)
    return PersonalCard(**{**base, **kw})


def test_ebay_title_says_reverse_and_first_edition_right_after_the_code():
    titolo = ebay_title(_carta(reverse=True, first_edition=True))
    assert "004/102 Reverse 1a Edizione Base Set" in titolo
    assert len(titolo) <= 80


def test_ebay_title_without_flags_is_unchanged():
    assert "Reverse" not in ebay_title(_carta())


def test_sold_search_only_looks_at_italy():
    assert "LH_PrefLoc=1" in ebay_sold_url(_carta())


def test_site_title_starts_with_the_game():
    from utils.card_listing import site_title
    assert site_title(_carta()).startswith("Pokémon · Charizard · Base Set 004/102")
    assert site_title(_carta(game_id=None)).startswith("Charizard ·")


def test_vinted_title_is_short_lowercase_and_italian():
    from utils.card_listing import vinted_description, vinted_title
    c = _carta(name="Spearow", name_it="Spearow", collection="EX Crystal Guardians",
               collection_it="EX Guardiani dei Cristalli", printed_code="061/100")
    assert vinted_title(c) == "Spearow 61 ex guardiani dei cristalli IT pokemon"
    assert vinted_description(c) == "Spearow 61 ex guardiani dei cristalli IT pokemon\nLingua italiano"


def test_vinted_title_keeps_letter_codes_and_flags():
    from utils.card_listing import vinted_title
    c = _carta(name="Mago Nero", printed_code="LOB-IT005", collection="Legend of Blue Eyes",
               game_id=4, reverse=True)
    assert vinted_title(c) == "Mago Nero LOB-IT005 reverse legend of blue eyes IT yu-gi-oh"


def test_vinted_price_is_cardtrader_minimum_plus_two_rounded_up():
    """La regola usata su Vinted: +2..3 € sul minimo, all'euro superiore."""
    from decimal import Decimal
    from utils.card_listing import vinted_price
    assert vinted_price(_carta(cardtrader_price=Decimal("2.60"))) == 5.0     # +2,40
    assert vinted_price(_carta(cardtrader_price=Decimal("12.10"))) == 15.0   # +2,90
    assert vinted_price(_carta(cardtrader_price=Decimal("3.00"))) == 5.0     # +2 esatti
    # Sopra i 15 € il ricarico cresce (+15% della parte sopra i 15), senza salti
    assert vinted_price(_carta(cardtrader_price=Decimal("15.00"))) == 17.0
    assert vinted_price(_carta(cardtrader_price=Decimal("20.00"))) == 23.0
    assert vinted_price(_carta(cardtrader_price=Decimal("30.00"))) == 35.0
    assert vinted_price(_carta(cardtrader_price=Decimal("50.00"))) == 58.0
    assert vinted_price(_carta(cardtrader_price=Decimal("100.00"))) == 115.0
    # Carte economiche: sotto 0,90 → 1 €; intorno all'euro (±0,10) → 2 €
    assert vinted_price(_carta(cardtrader_price=Decimal("0.13"))) == 1.0
    assert vinted_price(_carta(cardtrader_price=Decimal("0.89"))) == 1.0
    assert vinted_price(_carta(cardtrader_price=Decimal("0.90"))) == 2.0
    assert vinted_price(_carta(cardtrader_price=Decimal("1.10"))) == 2.0
    # Da 1,11 a 1,90 → 3 €, poi la regola +2 riprende senza salti
    assert vinted_price(_carta(cardtrader_price=Decimal("1.11"))) == 3.0
    assert vinted_price(_carta(cardtrader_price=Decimal("1.20"))) == 3.0
    assert vinted_price(_carta(cardtrader_price=Decimal("1.90"))) == 3.0
    assert vinted_price(_carta(cardtrader_price=Decimal("1.95"))) == 4.0
    # Senza minimo CardTrader: dal prezzo della carta
    assert vinted_price(_carta(cardtrader_price=None, list_price=Decimal("1.50"))) == 3.0  # scalino 1,11-1,90
    assert vinted_price(_carta(cardtrader_price=None)) is None
