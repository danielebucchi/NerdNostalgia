"""Unit test puri (no DB) per _calc_metrics dell'inventory.

Verifica le formule net_revenue / profit / immobilizzato / ancora_disponibile
isolatamente dai modelli SQLAlchemy.
"""
from decimal import Decimal
from types import SimpleNamespace

from api.inventory import _calc_metrics
from models.db import InventoryItemStatus


def _item(**kwargs) -> SimpleNamespace:
    """Costruisce un fake InventoryItem (duck typing)."""
    defaults = dict(
        sale_price=None,
        fee_amount=None,
        shipping_cost=None,
        cost=None,
        status="DRAFT",
        sold_date=None,
        quantity=1,
        quantity_sold=0,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_sold_item_basic_profit():
    """Venduto 100 con cost 30, no fee/shipping → profit 70."""
    item = _item(
        sale_price=Decimal("100"),
        cost=Decimal("30"),
        status=InventoryItemStatus.SOLD,
    )
    m = _calc_metrics(item)
    assert m["net_revenue"] == Decimal("100")
    assert m["profit"] == Decimal("70")
    assert m["immobilizzato"] == Decimal("0")


def test_sold_item_with_fee_and_shipping():
    """100 - fee 5 - shipping 3 - cost 30 → profit 62."""
    item = _item(
        sale_price=Decimal("100"),
        fee_amount=Decimal("5"),
        shipping_cost=Decimal("3"),
        cost=Decimal("30"),
        status=InventoryItemStatus.SOLD,
    )
    m = _calc_metrics(item)
    assert m["net_revenue"] == Decimal("92")
    assert m["profit"] == Decimal("62")


def test_unsold_item_has_immobilizzato():
    """Item con cost 50 ma non venduto → immobilizzato 50, profit 0."""
    item = _item(cost=Decimal("50"), status="DRAFT")
    m = _calc_metrics(item)
    assert m["profit"] == Decimal("0")
    assert m["net_revenue"] == Decimal("0")
    assert m["immobilizzato"] == Decimal("50")


def test_unsold_with_no_cost_no_immobilizzato():
    """Senza cost il pezzo non vale niente immobilizzato."""
    item = _item(status="DRAFT")
    m = _calc_metrics(item)
    assert m["immobilizzato"] == Decimal("0")


def test_sold_by_sold_date_only():
    """sold_date settato → considerato venduto anche se status != SOLD."""
    from datetime import date
    item = _item(
        sale_price=Decimal("50"),
        cost=Decimal("20"),
        sold_date=date(2026, 1, 1),
        status="LISTED",  # non SOLD
    )
    m = _calc_metrics(item)
    assert m["profit"] == Decimal("30")
    assert m["immobilizzato"] == Decimal("0")


def test_archived_item_not_ancora_disponibile():
    item = _item(status=InventoryItemStatus.ARCHIVED, quantity=3)
    m = _calc_metrics(item)
    assert m["ancora_disponibile"] is False


def test_partially_sold_still_available():
    """qty 5, venduti 2 → ancora_disponibile True."""
    item = _item(quantity=5, quantity_sold=2, status="LISTED")
    m = _calc_metrics(item)
    assert m["ancora_disponibile"] is True


def test_fully_sold_not_available():
    """qty 3, venduti 3 → considerato venduto, non disponibile."""
    item = _item(quantity=3, quantity_sold=3, status="LISTED")
    m = _calc_metrics(item)
    assert m["ancora_disponibile"] is False


def test_decimal_precision():
    """Verifica che funzioni con decimali fini (no float drift)."""
    item = _item(
        sale_price=Decimal("99.99"),
        fee_amount=Decimal("9.99"),
        shipping_cost=Decimal("0.01"),
        cost=Decimal("10.00"),
        status=InventoryItemStatus.SOLD,
    )
    m = _calc_metrics(item)
    assert m["net_revenue"] == Decimal("89.99")
    assert m["profit"] == Decimal("79.99")
