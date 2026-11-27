"""Prezzo delle carte sul sito: minimo 0,20, poi almeno 0,50."""
import pytest

from utils.card_listing import prezzo_sito


@pytest.mark.parametrize("prezzo, atteso", [
    (0.05, 0.20), (0.11, 0.20), (0.20, 0.20), (0.21, 0.50), (0.45, 0.50), (0.49, 0.50),
    (0.50, 0.50), (0.55, 0.55), (12.3, 12.3),
])
def test_minimum_site_price(prezzo, atteso):
    assert prezzo_sito(prezzo) == atteso
