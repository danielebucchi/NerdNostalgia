"""Collezione carte sciolte: lettura e scrittura base."""


def test_created_card_can_be_read_back(client, admin_headers):
    """created_at/updated_at arrivano dal DB come datetime: dichiarati str
    facevano fallire ogni risposta con 500."""
    r = client.post("/api/personal-cards/", json={"name": "Pikachu"}, headers=admin_headers)
    assert r.status_code == 201, r.text
    assert r.json()["created_at"]

    r = client.get("/api/personal-cards/", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["items"][0]["name"] == "Pikachu"
