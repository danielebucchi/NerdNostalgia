"""Prezzo delle carte sul sito: minimo 0,20, poi almeno 0,50."""
import pytest

from utils.card_listing import prezzo_sito


@pytest.mark.parametrize("prezzo, atteso", [
    (0.05, 0.20), (0.11, 0.20), (0.20, 0.20), (0.21, 0.50), (0.45, 0.50), (0.49, 0.50),
    (0.50, 0.50), (0.55, 0.55), (12.3, 12.3),
])
def test_minimum_site_price(prezzo, atteso):
    assert prezzo_sito(prezzo) == atteso


def test_blueprint_search_italian_names_and_reprint_numbers():
    from utils.cardtrader_sync import cerca_blueprint, numero_semplice
    bp = [{"id": 1, "name": "Arceus VSTAR", "fixed_properties": {"collector_number": "BRS 123"}},
          {"id": 2, "name": "Arceus V", "fixed_properties": {"collector_number": "BRS 122"}},
          {"id": 3, "name": "Charizard", "fixed_properties": {"collector_number": "004"}}]
    trova = lambda q: [b["id"] for b in cerca_blueprint(bp, q)]
    assert trova("arceus v astro") == [1]
    assert trova("123") == [1]
    assert trova("arceus") == [1, 2]
    assert trova("4") == [3] and trova("charizard") == [3]
    assert numero_semplice("BRS 123") == "123" and numero_semplice("004") == ""
