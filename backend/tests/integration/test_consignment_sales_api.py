"""Consignment sales: vendita per altri con commissione + mark-paid."""


def _payload(**override):
    base = {
        "sale_date": "2026-04-10",
        "item": "Action Figure Goku",
        "consignor": "Luca",
        "sale_price": "60.00",
        "commission_pct": "10",
        "fee_amount": "3.00",
        "shipping_cost": "5.00",
        "sold_platform": "Vinted",
        "sold_by": "io",
        "buyer": "anonimo",
    }
    base.update(override)
    return base


def test_create_consignment_sale(client, admin_headers):
    r = client.post("/api/consignment-sales/", headers=admin_headers, json=_payload())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["consignor"] == "Luca"
    assert body["paid_out"] is False
    # commission_amount esplicito non passato → backend calcola commission_effective
    # da commission_pct: 10% di 60 = 6.00
    assert float(body["commission_effective"]) == 6.00


def test_list_consignment_sales(client, admin_headers):
    client.post("/api/consignment-sales/", headers=admin_headers, json=_payload())
    client.post(
        "/api/consignment-sales/", headers=admin_headers,
        json=_payload(item="B", consignor="Mario"),
    )
    r = client.get("/api/consignment-sales/", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 2


def test_mark_paid(client, admin_headers):
    created = client.post(
        "/api/consignment-sales/", headers=admin_headers, json=_payload(),
    ).json()
    r = client.post(
        f"/api/consignment-sales/{created['id']}/mark-paid",
        headers=admin_headers,
        json={},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["paid_out"] is True
    assert body["payout_date"] is not None


def test_filter_paid_out(client, admin_headers):
    a = client.post(
        "/api/consignment-sales/", headers=admin_headers, json=_payload(item="A"),
    ).json()
    client.post(
        "/api/consignment-sales/", headers=admin_headers, json=_payload(item="B"),
    )
    client.post(
        f"/api/consignment-sales/{a['id']}/mark-paid",
        headers=admin_headers,
        json={},
    )

    r = client.get("/api/consignment-sales/?paid_out=true", headers=admin_headers)
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["item"] == "A"

    r2 = client.get("/api/consignment-sales/?paid_out=false", headers=admin_headers)
    items2 = r2.json()["items"]
    assert len(items2) == 1
    assert items2[0]["item"] == "B"


def test_delete_consignment_sale(client, admin_headers):
    created = client.post(
        "/api/consignment-sales/", headers=admin_headers, json=_payload(),
    ).json()
    r = client.delete(f"/api/consignment-sales/{created['id']}", headers=admin_headers)
    assert r.status_code == 204


def test_consignment_admin_required(client):
    r = client.post("/api/consignment-sales/", json=_payload())
    assert r.status_code == 401
