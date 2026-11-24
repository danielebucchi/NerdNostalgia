"""Unit: cosa dice il nome del file di uno scan ("93_PL_002.jpg")."""
import pytest

from utils.scan_filename import leggi


@pytest.mark.parametrize("nome, numero, condizione, prima, copia", [
    ("93_PL.jpg", "93", "Played", False, None),
    ("93_PL_002.jpg", "93", "Played", False, 2),
    ("66_1ed_SP.jpg", "66", "Slightly Played", True, None),
    ("48_NM.jpg", "48", "Near Mint", False, None),
    ("12_M_003.png", "12", "Mint", False, 3),
    ("7_MP.jpg", "7", "Moderately Played", False, None),
    ("5_PO.jpg", "5", "Poor", False, None),
    ("095_01.jpg", "95", None, False, 1),
    ("47.jpg", "47", None, False, None),
])
def test_reads_number_condition_first_edition_and_copy(nome, numero, condizione, prima, copia):
    d = leggi(nome)
    assert (d.numero, d.condizione, d.prima_edizione, d.copia) == (numero, condizione, prima, copia)


@pytest.mark.parametrize("nome", ["carta_1.jpg", "op08-076.jpg", "IMG_2024.jpg", "", None])
def test_names_without_the_convention_say_nothing_wrong(nome):
    d = leggi(nome)
    assert d.condizione is None and not d.prima_edizione
    # "IMG_2024": il numero non e' in testa, quindi non e' il numero della carta
    assert d.numero is None
