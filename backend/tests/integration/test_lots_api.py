"""Lots CRUD + auto-code + distribute-cost + bulk-publish."""
import pytest


@pytest.fixture()
def lot_payload():
    return {
        "title": "Lotto Game Boy",
        "purchase_date": "2026-01-15",
        "purchase_platform": "Subito",
        "bought_by": "io",
        "total_cost": "200.00",
    }


def test_create_lot_auto_code(client, admin_headers, lot_payload):
    r = client.post("/api/lots/", headers=admin_headers, json=lot_payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["code"] == "L0001"
    assert body["status"] == "OPEN"
    assert body["title"] == "Lotto Game Boy"


def test_create_second_lot_increments_code(client, admin_headers, lot_payload):
    client.post("/api/lots/", headers=admin_headers, json=lot_payload)
    r = client.post(
        "/api/lots/",
        headers=admin_headers,
        json={**lot_payload, "title": "Secondo lotto"},
    )
    assert r.status_code == 201
    assert r.json()["code"] == "L0002"


def test_list_lots(client, admin_headers, lot_payload):
    client.post("/api/lots/", headers=admin_headers, json=lot_payload)
    client.post("/api/lots/", headers=admin_headers, json={**lot_payload, "title": "B"})
    r = client.get("/api/lots/", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2


def test_get_lot_by_id(client, admin_headers, lot_payload):
    created = client.post("/api/lots/", headers=admin_headers, json=lot_payload).json()
    r = client.get(f"/api/lots/{created['id']}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["code"] == "L0001"


def test_get_lot_not_found(client, admin_headers):
    r = client.get("/api/lots/99999", headers=admin_headers)
    assert r.status_code == 404


def test_update_lot_status(client, admin_headers, lot_payload):
    created = client.post("/api/lots/", headers=admin_headers, json=lot_payload).json()
    r = client.patch(
        f"/api/lots/{created['id']}",
        headers=admin_headers,
        json={"status": "CLOSED"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "CLOSED"


def test_delete_lot(client, admin_headers, lot_payload):
    created = client.post("/api/lots/", headers=admin_headers, json=lot_payload).json()
    r = client.delete(f"/api/lots/{created['id']}", headers=admin_headers)
    assert r.status_code == 204
    # Verifica
    r2 = client.get(f"/api/lots/{created['id']}", headers=admin_headers)
    assert r2.status_code == 404


def test_lots_admin_required(client, lot_payload):
    """Lots endpoint richiede admin."""
    r = client.post("/api/lots/", json=lot_payload)
    assert r.status_code == 401


def test_distribute_cost_empty_lot_400(client, admin_headers, lot_payload):
    created = client.post("/api/lots/", headers=admin_headers, json=lot_payload).json()
    r = client.post(
        f"/api/lots/{created['id']}/distribute-cost",
        headers=admin_headers,
        json={"total_cost": "100.00"},
    )
    assert r.status_code == 400


def test_distribute_cost_with_items(client, admin_headers, db_session, lot_payload):
    """Distribuzione: total_cost 100 su 4 pezzi → unit_cost 25.00 ognuno."""
    from models.db import InventoryItem

    created = client.post("/api/lots/", headers=admin_headers, json=lot_payload).json()
    lot_id = created["id"]

    # Aggiungi item via DB (2 articoli, qty 2 + qty 2 = 4 pezzi totali)
    db_session.add_all([
        InventoryItem(lot_id=lot_id, title="Item A", quantity=2, status="DRAFT"),
        InventoryItem(lot_id=lot_id, title="Item B", quantity=2, status="DRAFT"),
    ])
    db_session.commit()

    r = client.post(
        f"/api/lots/{lot_id}/distribute-cost",
        headers=admin_headers,
        json={"total_cost": "100.00"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["items_updated"] == 2
    assert body["total_pieces"] == 4
    assert body["unit_cost"] == "25.00"
