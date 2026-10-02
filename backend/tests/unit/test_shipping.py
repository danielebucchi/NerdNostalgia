"""Unit: spedizione base + assicurazione facoltativa."""
from decimal import Decimal

import pytest

from helpers.shipping import (
    FREE_SHIPPING_FROM,
    INSURANCE_FEE,
    INSURED_BY_DEFAULT_FROM,
    base_shipping,
    calc_shipping,
    default_insured,
    insurance_fee,
    missing_for_free_shipping,
    resolve_insured,
)


@pytest.mark.parametrize("subtotal,expected", [
    ("0.01", "6.21"),
    ("10.00", "6.21"),
    ("25.00", "6.21"),      # il confine appartiene allo scaglione basso
    ("25.01", "7.21"),      # 4% = 1,0004 → sotto il minimo, resta 1,00
    ("35.00", "7.61"),      # 4% = 1,40
    ("50.00", "8.21"),      # 4% = 2,00
    ("100.00", "10.21"),    # 4% = 4,00
    ("150.00", "12.21"),    # 4% = 6,00: sotto il tetto di 6,21
    ("249.99", "12.42"),    # oltre il tetto: resta al massimo
    ("250.00", "0.00"),     # gratis
    ("900.00", "0.00"),
])
def test_base_shipping_bands(subtotal, expected):
    assert base_shipping(Decimal(subtotal)) == Decimal(expected)


def test_percentage_is_capped():
    """Il tetto sulla quota % esiste perche' l'etichetta costa uguale per un
    pacco da 30 € e per uno da 240 €: senza, chiederemmo 16 € di spedizione
    su un ordine da 249 €. Il tetto morde dove il 4% supera 6,21 €, cioe'
    da ~155 € in su."""
    assert base_shipping(Decimal("200")) == base_shipping(Decimal("249.99"))
    # Sotto quella soglia comanda ancora la percentuale
    assert base_shipping(Decimal("150")) < base_shipping(Decimal("200"))


def test_insurance_is_a_flat_fee():
    """Premio fisso, non percentuale: fino a 1.500 € di valore i corrieri
    applicano un minimo fisso."""
    assert insurance_fee(Decimal("10"), True) == INSURANCE_FEE
    assert insurance_fee(Decimal("200"), True) == INSURANCE_FEE
    assert insurance_fee(Decimal("200"), False) == Decimal("0.00")


def test_default_is_insured_from_fifty():
    assert default_insured(Decimal("49.99")) is False
    assert default_insured(Decimal("50.00")) is True
    assert INSURED_BY_DEFAULT_FROM == Decimal("50.00")


def test_buyer_can_override_in_both_directions():
    """Il punto della funzione: assicurare un ordine piccolo o rinunciare su
    uno grande."""
    # Ordine piccolo, assicurato per scelta
    assert calc_shipping(Decimal("10"), insured=True) == Decimal("12.11")
    assert calc_shipping(Decimal("10"), insured=False) == Decimal("6.21")
    # Ordine grande, scoperto per scelta
    assert calc_shipping(Decimal("100"), insured=False) == Decimal("10.21")
    assert calc_shipping(Decimal("100"), insured=True) == Decimal("16.11")


def test_none_means_use_the_default_for_the_band():
    assert calc_shipping(Decimal("10"), insured=None) == Decimal("6.21")
    assert calc_shipping(Decimal("100"), insured=None) == Decimal("16.11")


def test_above_free_threshold_insurance_is_included_and_not_removable():
    """Un pacco da 250 € non viaggia scoperto, e il premio non si paga."""
    assert resolve_insured(Decimal("300"), False) is True
    assert insurance_fee(Decimal("300"), True) == Decimal("0.00")
    assert calc_shipping(Decimal("300"), insured=False) == Decimal("0.00")


def test_carrello_vuoto_non_esplode():
    assert calc_shipping(0) == Decimal("6.21")
    assert calc_shipping(None) == Decimal("6.21")


def test_free_shipping_threshold_is_exposed():
    assert FREE_SHIPPING_FROM == Decimal("250.00")


@pytest.mark.parametrize("subtotal,missing", [
    ("0", "250.00"),
    ("50", "200.00"),
    ("249.99", "0.01"),
    ("250", "0.00"),
])
def test_missing_for_free_shipping(subtotal, missing):
    assert missing_for_free_shipping(Decimal(subtotal)) == Decimal(missing)
