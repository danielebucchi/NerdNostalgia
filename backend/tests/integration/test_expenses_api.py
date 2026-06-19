"""Expenses CRUD + filtri flag related_to_cards / related_to_creations."""


def _payload(**override):
    base = {
        "spend_date": "2026-03-01",
        "item": "Bustine protettive",
        "category": "consumabili",
        "amount": "15.50",
        "paid_by": "io",
        "related_to_cards": False,
        "related_to_creations": False,
    }
    base.update(override)
    return base


def test_create_expense(client, admin_headers):
    r = client.post("/api/expenses/", headers=admin_headers, json=_payload())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["item"] == "Bustine protettive"
    assert body["related_to_cards"] is False


def test_list_expenses(client, admin_headers):
    client.post("/api/expenses/", headers=admin_headers, json=_payload(item="A"))
    client.post("/api/expenses/", headers=admin_headers, json=_payload(item="B"))
    r = client.get("/api/expenses/", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 2


def test_filter_related_to_cards(client, admin_headers):
    client.post(
        "/api/expenses/", headers=admin_headers,
        json=_payload(item="Toploader", related_to_cards=True),
    )
    client.post(
        "/api/expenses/", headers=admin_headers,
        json=_payload(item="Caffe", related_to_cards=False),
    )
    r = client.get(
        "/api/expenses/?related_to_cards=true", headers=admin_headers,
    )
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["item"] == "Toploader"


def test_update_expense(client, admin_headers):
    created = client.post(
        "/api/expenses/", headers=admin_headers, json=_payload(),
    ).json()
    r = client.patch(
        f"/api/expenses/{created['id']}",
        headers=admin_headers,
        json={"amount": "20.00", "category": "altro"},
    )
    assert r.status_code == 200
    body = r.json()
    assert float(body["amount"]) == 20.00
    assert body["category"] == "altro"


def test_delete_expense(client, admin_headers):
    created = client.post(
        "/api/expenses/", headers=admin_headers, json=_payload(),
    ).json()
    r = client.delete(f"/api/expenses/{created['id']}", headers=admin_headers)
    assert r.status_code == 204


def test_expenses_admin_required(client):
    r = client.post("/api/expenses/", json=_payload())
    assert r.status_code == 401
