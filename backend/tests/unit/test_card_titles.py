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
