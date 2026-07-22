"""Unit: config eBay + OAuth (consent URL, scambio code, cache access token)."""
import time

import pytest

from utils import ebay_client as eb


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("EBAY_ENV", "sandbox")
    monkeypatch.setenv("EBAY_MARKETPLACE_ID", "EBAY_IT")
    monkeypatch.setenv("EBAY_CLIENT_ID", "cid")
    monkeypatch.setenv("EBAY_CLIENT_SECRET", "sec")
    monkeypatch.setenv("EBAY_REDIRECT_RUNAME", "RuName-123")
    monkeypatch.delenv("EBAY_REFRESH_TOKEN", raising=False)
    eb._TOKEN["value"] = None
    eb._TOKEN["exp"] = 0.0
    yield


class _Resp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.content = b"x"

    def json(self):
        return self._payload


def test_environment_urls():
    assert eb.is_sandbox() is True
    assert eb._api_base() == "https://api.sandbox.ebay.com"
    assert eb._auth_host() == "auth.sandbox.ebay.com"


def test_configured_flags():
    assert eb.can_start_consent() is True
    assert eb.is_configured() is False  # manca il refresh token
    import os
    os.environ["EBAY_REFRESH_TOKEN"] = "rt"
    try:
        assert eb.is_configured() is True
    finally:
        del os.environ["EBAY_REFRESH_TOKEN"]


def test_consent_url_contains_scopes_and_runame():
    url = eb.consent_url()
    assert url.startswith("https://auth.sandbox.ebay.com/oauth2/authorize?")
    assert "client_id=cid" in url
    assert "redirect_uri=RuName-123" in url
    assert "sell.inventory" in url


def test_exchange_code(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, data=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        return _Resp(200, {"refresh_token": "RT", "refresh_token_expires_in": 47304000})

    monkeypatch.setattr(eb.requests, "post", fake_post)
    out = eb.exchange_code("the-code")
    assert out["refresh_token"] == "RT"
    assert captured["data"]["grant_type"] == "authorization_code"
    assert captured["data"]["code"] == "the-code"


def test_access_token_cached(monkeypatch):
    monkeypatch.setenv("EBAY_REFRESH_TOKEN", "rt")
    calls = {"n": 0}

    def fake_post(url, headers=None, data=None, timeout=None):
        calls["n"] += 1
        return _Resp(200, {"access_token": "AT%d" % calls["n"], "expires_in": 7200})

    monkeypatch.setattr(eb.requests, "post", fake_post)
    t1 = eb._access_token()
    t2 = eb._access_token()
    assert t1 == t2 == "AT1"
    assert calls["n"] == 1  # secondo giro dalla cache

    # scaduto → rinnova
    eb._TOKEN["exp"] = time.time() - 1
    t3 = eb._access_token()
    assert t3 == "AT2"
    assert calls["n"] == 2
