"""Inventory items: CRUD + lot scoping + totali aggregati."""
import pytest


@pytest.fixture()
def lot_id(client, admin_headers):
    r = client.post(
        "/api/lots/",
        headers=admin_headers,
        json={"title": "Lotto test", "total_cost": "100.00"},
    )
    return r.json()["id"]


def test_create_item_under_lot(client, admin_headers, lot_id):
    r = client.post(
        "/api/inventory/",
        headers=admin_headers,
        json={"lot_id": lot_id, "title": "Console", "quantity": 1, "cost": "50.00"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["lot_id"] == lot_id
    assert body["title"] == "Console"
    assert body["status"] == "DRAFT"


def test_create_item_unknown_lot_404(client, admin_headers):
    r = client.post(
        "/api/inventory/",
        headers=admin_headers,
        json={"lot_id": 99999, "title": "X", "quantity": 1},
    )
    assert r.status_code == 404


def test_list_items_filter_by_lot(client, admin_headers, lot_id):
    """Crea 2 item in 2 lotti diversi e verifica filtro."""
    other_lot = client.post(
        "/api/lots/", headers=admin_headers, json={"title": "Altro"}
    ).json()["id"]

    client.post(
        "/api/inventory/",
        headers=admin_headers,
        json={"lot_id": lot_id, "title": "A", "quantity": 1},
    )
    client.post(
        "/api/inventory/",
        headers=admin_headers,
        json={"lot_id": other_lot, "title": "B", "quantity": 1},
    )

    r = client.get(f"/api/inventory/?lot_id={lot_id}", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "A"


def test_list_totals_aggregation(client, admin_headers, lot_id):
    """Totali: 1 item venduto a 100 con cost 30 → profit 70, revenue 100."""
    client.post(
        "/api/inventory/",
        headers=admin_headers,
        json={
            "lot_id": lot_id,
            "title": "Venduto",
            "quantity": 1,
            "cost": "30.00",
            "sale_price": "100.00",
            "sold_date": "2026-01-01",
            "status": "SOLD",
        },
    )

    r = client.get("/api/inventory/", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    # Sale price 100 e cost 30 -> revenue 100, profit 70
    assert float(body["total_revenue"]) == 100.00
    assert float(body["total_cost"]) == 30.00
    assert float(body["total_profit"]) == 70.00


def test_update_item_status(client, admin_headers, lot_id):
    item = client.post(
        "/api/inventory/",
        headers=admin_headers,
        json={"lot_id": lot_id, "title": "Y", "quantity": 1},
    ).json()
    r = client.patch(
        f"/api/inventory/{item['id']}/status",
        headers=admin_headers,
        json={"status": "ARCHIVED"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ARCHIVED"


def test_delete_item(client, admin_headers, lot_id):
    item = client.post(
        "/api/inventory/",
        headers=admin_headers,
        json={"lot_id": lot_id, "title": "Z", "quantity": 1},
    ).json()
    r = client.delete(f"/api/inventory/{item['id']}", headers=admin_headers)
    assert r.status_code == 204
