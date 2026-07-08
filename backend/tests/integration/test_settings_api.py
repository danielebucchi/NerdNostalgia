"""Settings runtime: public endpoint, admin CRUD, whitelist pubblica."""
from helpers.setting import SETTINGS_SPEC


def test_public_settings_returns_defaults(client):
    r = client.get("/api/settings/public")
    assert r.status_code == 200
    body = r.json()
    # Solo chiavi pubbliche
    for key in body:
        assert SETTINGS_SPEC[key]["public"] is True
    # Le admin-only NON devono uscire
    assert "marketplace_footer_vinted" not in body
    # Default effettivi
    assert body["hand_exchange_cap_prefixes"] == "56,57"
    assert body["contact_email"] == "nerdnostalgiaita@gmail.com"


def test_public_settings_no_auth_needed(client):
    r = client.get("/api/settings/public")
    assert r.status_code == 200


def test_list_settings_requires_admin(client):
    r = client.get("/api/settings/")
    assert r.status_code == 401


def test_update_and_effective_value(client, admin_headers):
    r = client.put(
        "/api/settings/",
        headers=admin_headers,
        json={"values": {"paypal_me": "TestHandle", "contact_whatsapp": "3331234567"}},
    )
    assert r.status_code == 200, r.text
    entries = {e["key"]: e for e in r.json()}
    assert entries["paypal_me"]["value"] == "TestHandle"
    assert entries["paypal_me"]["effective"] == "TestHandle"

    # Il pubblico vede il nuovo valore
    pub = client.get("/api/settings/public").json()
    assert pub["paypal_me"] == "TestHandle"
    assert pub["contact_whatsapp"] == "3331234567"


def test_update_unknown_key_400(client, admin_headers):
    r = client.put(
        "/api/settings/",
        headers=admin_headers,
        json={"values": {"not_a_real_key": "x"}},
    )
    assert r.status_code == 400


def test_empty_value_falls_back_to_default(client, admin_headers):
    client.put(
        "/api/settings/",
        headers=admin_headers,
        json={"values": {"hand_exchange_cap_prefixes": "50,51"}},
    )
    assert client.get("/api/settings/public").json()["hand_exchange_cap_prefixes"] == "50,51"

    # Svuotare = tornare al default
    client.put(
        "/api/settings/",
        headers=admin_headers,
        json={"values": {"hand_exchange_cap_prefixes": ""}},
    )
    assert client.get("/api/settings/public").json()["hand_exchange_cap_prefixes"] == "56,57"
