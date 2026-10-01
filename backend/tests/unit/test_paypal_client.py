"""Unit: client PayPal (config, ordine, cattura, firma webhook)."""
from decimal import Decimal

import pytest

from utils import paypal_client as pp


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("PAYPAL_ENV", "sandbox")
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "cid")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "secret")
    monkeypatch.delenv("PAYPAL_WEBHOOK_ID", raising=False)
    pp._TOKEN["value"] = None
    pp._TOKEN["exp"] = 0.0
    yield


class _Item:
    def __init__(self, title, price, qty=1):
        self.title_snapshot = title
        self.price_snapshot = Decimal(price)
        self.quantity = qty


class _Order:
    def __init__(self):
        self.id = 42
        self.currency = "EUR"
        self.shipping_total = Decimal("5.00")
        self.grand_total = Decimal("13.00")
        self.items = [_Item("Controller xbox 360", "8.00")]


def test_sandbox_is_the_default_environment(monkeypatch):
    monkeypatch.delenv("PAYPAL_ENV", raising=False)
    assert pp.is_sandbox() is True
    assert pp._api_base() == "https://api-m.sandbox.paypal.com"


def test_live_environment_switches_host(monkeypatch):
    monkeypatch.setenv("PAYPAL_ENV", "live")
    assert pp.is_sandbox() is False
    assert pp._api_base() == "https://api-m.paypal.com"


def test_public_config_never_leaks_the_secret():
    cfg = pp.public_config()
    assert cfg["configured"] is True
    assert cfg["client_id"] == "cid"
    assert "secret" not in str(cfg)


def test_not_configured_without_credentials(monkeypatch):
    monkeypatch.delenv("PAYPAL_CLIENT_ID", raising=False)
    assert pp.is_configured() is False
    assert pp.public_config()["client_id"] == ""


def test_create_order_sends_server_side_totals(monkeypatch):
    seen = {}

    def fake_request(method, path, **kwargs):
        seen["method"] = method
        seen["path"] = path
        seen["json"] = kwargs.get("json")
        return {"id": "PP-ORDER-1"}

    monkeypatch.setattr(pp, "_request", fake_request)
    out = pp.create_order(_Order(), "https://nerdnostalgia.store")

    assert out["id"] == "PP-ORDER-1"
    assert seen["path"] == "/v2/checkout/orders"
    unit = seen["json"]["purchase_units"][0]
    # L'importo lo decide il server, e deve quadrare col nostro ordine
    assert unit["amount"]["value"] == "13.00"
    assert unit["amount"]["breakdown"]["item_total"]["value"] == "8.00"
    assert unit["amount"]["breakdown"]["shipping"]["value"] == "5.00"
    # custom_id serve al webhook per ritrovare l'ordine
    assert unit["custom_id"] == "42"
    # L'indirizzo lo abbiamo gia': non lo richiediamo di nuovo a PayPal
    assert seen["json"]["application_context"]["shipping_preference"] == "NO_SHIPPING"


def test_capture_id_is_extracted():
    payload = {
        "status": "COMPLETED",
        "purchase_units": [
            {"payments": {"captures": [{"id": "CAP-9"}]}},
        ],
    }
    assert pp.is_completed(payload) is True
    assert pp.capture_id_from(payload) == "CAP-9"


def test_capture_id_missing_is_not_an_error():
    assert pp.capture_id_from({}) is None
    assert pp.capture_id_from({"purchase_units": [{}]}) is None
    assert pp.is_completed({"status": "PENDING"}) is False


def test_webhook_refused_without_webhook_id():
    """Senza webhook id non possiamo verificare la firma: meglio rifiutare
    che fidarsi di chiunque conosca l'URL."""
    assert pp.verify_webhook({"Paypal-Transmission-Id": "x"}, "{}") is False


def test_webhook_refused_when_headers_are_missing(monkeypatch):
    monkeypatch.setenv("PAYPAL_WEBHOOK_ID", "WH-1")
    assert pp.verify_webhook({}, "{}") is False


def test_webhook_accepted_when_paypal_says_success(monkeypatch):
    monkeypatch.setenv("PAYPAL_WEBHOOK_ID", "WH-1")
    monkeypatch.setattr(
        pp, "_request", lambda *a, **k: {"verification_status": "SUCCESS"}
    )
    headers = {
        "Paypal-Transmission-Id": "t", "Paypal-Transmission-Sig": "s",
        "Paypal-Cert-Url": "https://paypal.com/cert", "Paypal-Auth-Algo": "SHA256",
        "Paypal-Transmission-Time": "2026-10-01T00:00:00Z",
    }
    assert pp.verify_webhook(headers, "{}") is True


def test_webhook_refused_when_paypal_says_failure(monkeypatch):
    monkeypatch.setenv("PAYPAL_WEBHOOK_ID", "WH-1")
    monkeypatch.setattr(
        pp, "_request", lambda *a, **k: {"verification_status": "FAILURE"}
    )
    headers = {
        "Paypal-Transmission-Id": "t", "Paypal-Transmission-Sig": "s",
        "Paypal-Cert-Url": "https://paypal.com/cert", "Paypal-Auth-Algo": "SHA256",
        "Paypal-Transmission-Time": "2026-10-01T00:00:00Z",
    }
    assert pp.verify_webhook(headers, "{}") is False
