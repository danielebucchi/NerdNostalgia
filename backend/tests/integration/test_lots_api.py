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


def test_duplicate_lot_clones_metadata_and_items(client, admin_headers, lot_payload):
    src = client.post("/api/lots/", headers=admin_headers, json=lot_payload).json()
    client.post(
        "/api/inventory/",
        headers=admin_headers,
        json={"lot_id": src["id"], "title": "A", "cost": "10.00",
              "list_price": "25.00", "quantity": 1},
    )
    client.post(
        "/api/inventory/",
        headers=admin_headers,
        json={"lot_id": src["id"], "title": "B", "cost": "5.00", "quantity": 2},
    )

    r = client.post(
        f"/api/lots/{src['id']}/duplicate",
        headers=admin_headers,
        json={"copy_items": True, "title_prefix": "Copia di "},
    )
    assert r.status_code == 201, r.text
    dup = r.json()
    assert dup["id"] != src["id"]
    assert dup["code"] != src["code"]  # nuovo code sequenziale
    assert dup["title"].startswith("Copia di ")
    assert dup["purchase_platform"] == src["purchase_platform"]
    assert dup["status"] == "OPEN"

    items = client.get(
        f"/api/inventory/?lot_id={dup['id']}", headers=admin_headers,
    ).json()["items"]
    assert len(items) == 2
    titles = sorted(i["title"] for i in items)
    assert titles == ["A", "B"]
    # I clonati partono DRAFT senza vendite / foto / article link
    for it in items:
        assert it["status"] == "DRAFT"
        assert it["sale_price"] is None
        assert it["images"] == []
        assert it["article_id"] is None
    # ma list_price e cost sono conservati (template intatto)
    item_a = next(i for i in items if i["title"] == "A")
    assert float(item_a["list_price"]) == 25.00
    assert float(item_a["cost"]) == 10.00


def test_duplicate_lot_without_items(client, admin_headers, lot_payload):
    src = client.post("/api/lots/", headers=admin_headers, json=lot_payload).json()
    client.post(
        "/api/inventory/",
        headers=admin_headers,
        json={"lot_id": src["id"], "title": "A", "quantity": 1},
    )
    r = client.post(
        f"/api/lots/{src['id']}/duplicate",
        headers=admin_headers,
        json={"copy_items": False},
    )
    assert r.status_code == 201
    dup = r.json()
    items = client.get(
        f"/api/inventory/?lot_id={dup['id']}", headers=admin_headers,
    ).json()["items"]
    assert items == []


def test_duplicate_lot_not_found(client, admin_headers):
    r = client.post(
        "/api/lots/99999/duplicate", headers=admin_headers, json={},
    )
    assert r.status_code == 404
