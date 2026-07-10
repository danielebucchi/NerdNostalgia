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


# ---------------------------------------------------------------------------
# Immagini: upload / delete / reorder / propagazione a publish_to_site
# ---------------------------------------------------------------------------

import io  # noqa: E402
from PIL import Image  # noqa: E402


def _tiny_png_bytes(color: tuple = (200, 100, 50)) -> bytes:
    """Genera un PNG 4x4 unico per test. Il contenuto non conta, serve solo
    che sia decodificabile da PIL nella pipeline di save_upload."""
    img = Image.new("RGB", (4, 4), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture()
def item_id(client, admin_headers, lot_id):
    r = client.post(
        "/api/inventory/",
        headers=admin_headers,
        json={"lot_id": lot_id, "title": "Con foto", "quantity": 1},
    )
    return r.json()["id"]


def test_upload_inventory_image_appends_url(client, admin_headers, item_id):
    r = client.post(
        f"/api/inventory/{item_id}/upload-image",
        headers=admin_headers,
        files={"file": ("a.png", _tiny_png_bytes(), "image/png")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["images"]) == 1
    assert body["images"][0].endswith(".webp")
    assert f"/inventory/{item_id}/" in body["images"][0]


def test_upload_inventory_image_rejects_non_image(client, admin_headers, item_id):
    r = client.post(
        f"/api/inventory/{item_id}/upload-image",
        headers=admin_headers,
        files={"file": ("bad.txt", b"not an image", "text/plain")},
    )
    assert r.status_code == 400


def test_download_images_zip(client, admin_headers, item_id):
    """Lo zip contiene le foto full-size dell'item, nominate in ordine."""
    import io as _io
    import zipfile

    for color in ((10, 20, 30), (200, 100, 50)):
        client.post(
            f"/api/inventory/{item_id}/upload-image",
            headers=admin_headers,
            files={"file": ("a.png", _tiny_png_bytes(color), "image/png")},
        )

    r = client.get(f"/api/inventory/{item_id}/images.zip", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(_io.BytesIO(r.content))
    names = sorted(zf.namelist())
    assert names == [f"item-{item_id}-01.webp", f"item-{item_id}-02.webp"]
    # I file dentro non sono vuoti
    assert all(zf.getinfo(n).file_size > 0 for n in names)


def test_download_images_zip_empty_404(client, admin_headers, item_id):
    r = client.get(f"/api/inventory/{item_id}/images.zip", headers=admin_headers)
    assert r.status_code == 404


def test_delete_inventory_image_removes_url(client, admin_headers, item_id):
    up = client.post(
        f"/api/inventory/{item_id}/upload-image",
        headers=admin_headers,
        files={"file": ("a.png", _tiny_png_bytes(), "image/png")},
    ).json()
    url = up["images"][0]
    r = client.delete(
        f"/api/inventory/{item_id}/images",
        headers=admin_headers,
        params={"url": url},
    )
    assert r.status_code == 200
    assert r.json()["images"] == []


def test_reorder_inventory_images(client, admin_headers, item_id):
    a = client.post(
        f"/api/inventory/{item_id}/upload-image",
        headers=admin_headers,
        files={"file": ("a.png", _tiny_png_bytes((10, 10, 10)), "image/png")},
    ).json()["images"][0]
    both = client.post(
        f"/api/inventory/{item_id}/upload-image",
        headers=admin_headers,
        files={"file": ("b.png", _tiny_png_bytes((200, 200, 200)), "image/png")},
    ).json()["images"]
    assert both[0] == a and len(both) == 2
    b = both[1]

    r = client.put(
        f"/api/inventory/{item_id}/images",
        headers=admin_headers,
        json={"images": [b, a]},
    )
    assert r.status_code == 200
    assert r.json()["images"] == [b, a]


def test_reorder_rejects_non_permutation(client, admin_headers, item_id):
    up = client.post(
        f"/api/inventory/{item_id}/upload-image",
        headers=admin_headers,
        files={"file": ("a.png", _tiny_png_bytes(), "image/png")},
    ).json()
    r = client.put(
        f"/api/inventory/{item_id}/images",
        headers=admin_headers,
        json={"images": up["images"] + ["https://external.example/x.webp"]},
    )
    assert r.status_code == 400


def test_publish_uses_list_price_when_set(client, admin_headers, lot_id):
    """list_price ha priorita' su sale_price come Article.price."""
    item = client.post(
        "/api/inventory/",
        headers=admin_headers,
        json={
            "lot_id": lot_id,
            "title": "Con listino",
            "quantity": 1,
            "list_price": "25.00",
            "sale_price": "40.00",
        },
    ).json()

    r = client.post(
        f"/api/inventory/{item['id']}/publish",
        headers=admin_headers,
        json={},
    )
    assert r.status_code == 200, r.text
    article_id = r.json()["article_id"]
    art = client.get(f"/api/articles/{article_id}", headers=admin_headers).json()
    assert float(art["price"]) == 25.00


def test_publish_now_goes_live(client, admin_headers, lot_id):
    """publish_now=True → Article PUBLISHED con published_at, item LISTED."""
    item = client.post(
        "/api/inventory/",
        headers=admin_headers,
        json={"lot_id": lot_id, "title": "Diretto online", "quantity": 1,
              "list_price": "30.00"},
    ).json()

    r = client.post(
        f"/api/inventory/{item['id']}/publish",
        headers=admin_headers,
        json={"publish_now": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "LISTED"

    art = client.get(f"/api/articles/{body['article_id']}").json()
    assert art["status"] == "PUBLISHED"
    assert float(art["price"]) == 30.00


def test_bulk_publish_now(client, admin_headers, lot_id):
    """bulk-publish con publish_now=True pubblica direttamente e usa list_price."""
    ids = []
    for n in range(2):
        item = client.post(
            "/api/inventory/",
            headers=admin_headers,
            json={"lot_id": lot_id, "title": f"Bulk {n}", "quantity": 1,
                  "list_price": "12.00"},
        ).json()
        ids.append(item["id"])

    r = client.post(
        f"/api/lots/{lot_id}/bulk-publish",
        headers=admin_headers,
        json={"item_ids": ids, "publish_now": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["created"] == 2

    for item_id in ids:
        items = client.get(
            f"/api/inventory/?lot_id={lot_id}", headers=admin_headers,
        ).json()["items"]
        it = next(i for i in items if i["id"] == item_id)
        assert it["status"] == "LISTED"
        art = client.get(f"/api/articles/{it['article_id']}").json()
        assert art["status"] == "PUBLISHED"
        assert float(art["price"]) == 12.00


def test_publish_falls_back_to_sale_price(client, admin_headers, lot_id):
    """Se list_price e' None, la vecchia logica su sale_price resta valida."""
    item = client.post(
        "/api/inventory/",
        headers=admin_headers,
        json={
            "lot_id": lot_id,
            "title": "Solo ricavo",
            "quantity": 1,
            "sale_price": "18.50",
        },
    ).json()

    r = client.post(
        f"/api/inventory/{item['id']}/publish",
        headers=admin_headers,
        json={},
    )
    assert r.status_code == 200
    article_id = r.json()["article_id"]
    art = client.get(f"/api/articles/{article_id}", headers=admin_headers).json()
    assert float(art["price"]) == 18.50


def test_publish_to_site_copies_images_to_article(client, admin_headers, item_id):
    """Il publish deve copiare item.images → article.images. E' la ragione
    per cui carichiamo le foto sull'inventory item invece che sull'articolo."""
    client.post(
        f"/api/inventory/{item_id}/upload-image",
        headers=admin_headers,
        files={"file": ("a.png", _tiny_png_bytes(), "image/png")},
    )
    r = client.post(
        f"/api/inventory/{item_id}/publish",
        headers=admin_headers,
        json={},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    article_id = body["article_id"]
    assert article_id

    art = client.get(f"/api/articles/{article_id}", headers=admin_headers)
    assert art.status_code == 200
    assert len(art.json()["images"]) == 1
