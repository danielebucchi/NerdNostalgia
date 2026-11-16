"""Unit: niente righe che eBay legge come vendita fuori da eBay."""
import pytest

from utils.card_listing import senza_contatti_esterni


@pytest.mark.parametrize("riga", [
    "Altri pezzi su www.nerdnostalgia.store",
    "nerdnostalgia.store",
    "https://nerdnostalgia.store/articles/12",
    "Scrivimi a pippo@gmail.com",
    "WhatsApp 333 123 4567",
    "Tel. +39 3331234567",
    "Trovi altro sul mio Vinted",
    "Seguimi su Instagram",
])
def test_scarta_le_righe_fuori_ebay(riga):
    assert senza_contatti_esterni(f"Spedizione Veloce\n{riga}") == "Spedizione Veloce"


@pytest.mark.parametrize("riga", [
    "Spedizione Veloce",
    "Numero 025/198",
    "Uscita 12/03/2004",
    "Condizione: Near Mint",
])
def test_tiene_le_righe_normali(riga):
    assert senza_contatti_esterni(riga) == riga
