"""Dashboard /api/dashboard/totali: verifica calcoli aggregati."""
from datetime import date
from decimal import Decimal

import pytest


@pytest.fixture()
def seed_dashboard(client, admin_headers, db_session):
    """Crea uno scenario noto:
    - 1 lotto con 2 items
      * item venduto a 100, cost 30, fee 5, shipping 3 → profit = 100-30-5-3=62
      * item non venduto (immobilizzato), cost 20
    - 1 misc_sale esterna 50€
    """
    from models.db import InventoryItem, MiscSale

    lot = client.post(
        "/api/lots/",
        headers=admin_headers,
        json={
            "title": "Scenario dashboard",
            "purchase_date": "2026-01-10",
            "total_cost": "50.00",
        },
    ).json()

    db_session.add_all([
        InventoryItem(
            lot_id=lot["id"],
            title="Venduto",
            quantity=1,
            cost=Decimal("30.00"),
            sale_price=Decimal("100.00"),
            fee_amount=Decimal("5.00"),
            shipping_cost=Decimal("3.00"),
            sold_date=date(2026, 2, 10),
            status="SOLD",
        ),
        InventoryItem(
            lot_id=lot["id"],
            title="Immobilizzato",
            quantity=1,
            cost=Decimal("20.00"),
            status="DRAFT",
        ),
        MiscSale(
            sale_date=date(2026, 3, 10),
            item="Polaroid",
            amount=Decimal("50.00"),
            seller="io",
            platform="Vinted",
            paid_by_buyer=True,
            kind="external",
        ),
    ])
    db_session.commit()
    return lot


def test_dashboard_year_totals(client, admin_headers, seed_dashboard):
    r = client.get("/api/dashboard/totali?year=2026", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["year"] == 2026
    # Item venduto: revenue 100, cost 30, fee 5, shipping 3 -> profit 62
    assert Decimal(body["total_revenue"]) == Decimal("100.00")
    assert Decimal(body["total_cost"]) == Decimal("30.00")
    assert Decimal(body["total_fees"]) == Decimal("5.00")
    assert Decimal(body["total_shipping"]) == Decimal("3.00")
    assert Decimal(body["total_profit"]) == Decimal("62.00")
    # Immobilizzato: item non venduto con cost 20 in un lotto del 2026
    assert Decimal(body["total_immobilizzato"]) == Decimal("20.00")
    # Items_sold = 1, items_available = 1
    assert body["items_sold"] == 1
    assert body["items_available"] == 1


def test_dashboard_external_sales_recap(client, admin_headers, seed_dashboard):
    r = client.get("/api/dashboard/totali?year=2026", headers=admin_headers)
    body = r.json()
    # MiscSale 50€ esterna
    assert Decimal(body["misc_revenue"]) == Decimal("50.00")
    assert body["external_sales"]["count"] == 1


def test_dashboard_different_year_no_data(client, admin_headers, seed_dashboard):
    r = client.get("/api/dashboard/totali?year=2027", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["year"] == 2027
    # Niente vendite in 2027
    assert Decimal(body["total_revenue"]) == Decimal("0")
    assert body["items_sold"] == 0


def test_dashboard_requires_admin(client):
    r = client.get("/api/dashboard/totali")
    assert r.status_code == 401
