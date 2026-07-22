"""Unit: firma HMAC-SHA256 del client Vinted Pro (canonical string da doc VPI)."""
import hashlib
import hmac
import json

import pytest

from utils import vinted_pro_client as vp


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("VINTED_PRO_ENV", "sandbox")
    monkeypatch.setenv("VINTED_PRO_ACCESS_KEY", "AK")
    monkeypatch.setenv("VINTED_PRO_SIGNING_KEY", "SK")
    yield


def test_env_and_base_url():
    assert vp.is_sandbox() is True
    assert vp._base_url() == "https://pro-public-sandbox.svc.vinted.com"
    assert vp.is_configured() is True


def test_sign_matches_documented_canonical():
    ts = 1704067200
    method = "POST"
    path = "/api/v1/webhooks"
    body = '{"x":1}'
    canonical = f"{ts}.POST.{path}.AK.{body}"
    expected = hmac.new(b"SK", canonical.encode(), hashlib.sha256).hexdigest()
    assert vp._sign(ts, method, path, body) == expected


class _Resp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"ok": True}
        self.content = b"{}"

    def json(self):
        return self._payload


def test_request_headers_and_signature(monkeypatch):
    monkeypatch.setattr(vp.time, "time", lambda: 1700000000.9)  # ts=1700000000
    captured = {}

    def fake_request(method, url, headers=None, data=None, timeout=None):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = headers
        captured["data"] = data
        return _Resp()

    monkeypatch.setattr(vp.requests, "request", fake_request)
    vp.create_items([{"title": "Carta"}])

    h = captured["headers"]
    assert h["X-Vpi-Access-Key"] == "AK"
    assert h["X-Vpi-Hmac-Sha256"].startswith("t=1700000000,v1=")

    # la firma nell'header deve valere ESATTAMENTE sul body inviato
    sent_body = captured["data"].decode()
    sig = h["X-Vpi-Hmac-Sha256"].split("v1=")[1]
    canonical = f"1700000000.POST./api/v1/items.AK.{sent_body}"
    expected = hmac.new(b"SK", canonical.encode(), hashlib.sha256).hexdigest()
    assert sig == expected
    # e il body è quello atteso (items wrappati)
    assert json.loads(sent_body) == {"items": [{"title": "Carta"}]}


def test_request_signs_query_in_path(monkeypatch):
    monkeypatch.setattr(vp.time, "time", lambda: 1700000000.0)
    captured = {}

    def fake_request(method, url, headers=None, data=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        return _Resp(payload=[])

    monkeypatch.setattr(vp.requests, "request", fake_request)
    vp.get_items({"page": 2, "per_page": 50})

    # query ordinata e inclusa sia nell'URL sia nella firma
    assert captured["url"].endswith("/api/v1/items?page=2&per_page=50")
    sig = captured["headers"]["X-Vpi-Hmac-Sha256"].split("v1=")[1]
    canonical = "1700000000.GET./api/v1/items?page=2&per_page=50.AK."
    expected = hmac.new(b"SK", canonical.encode(), hashlib.sha256).hexdigest()
    assert sig == expected


def test_not_configured_raises(monkeypatch):
    monkeypatch.delenv("VINTED_PRO_ACCESS_KEY", raising=False)
    monkeypatch.delenv("VINTED_PRO_SIGNING_KEY", raising=False)
    assert vp.is_configured() is False
    with pytest.raises(vp.VintedProError):
        vp.get_ontologies()
