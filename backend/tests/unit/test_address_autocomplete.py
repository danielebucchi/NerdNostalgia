"""Unit: suggerimenti indirizzo (Geoapify) — normalizzazione e degrado soft."""
import pytest
import requests

from utils import address_autocomplete as aa


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("GEOAPIFY_API_KEY", "k-test")
    monkeypatch.delenv("ADDRESS_COUNTRY_CODES", raising=False)
    yield


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _feature(**props):
    return {"properties": props}


def test_not_configured_without_key(monkeypatch):
    monkeypatch.delenv("GEOAPIFY_API_KEY", raising=False)
    assert aa.is_configured() is False
    # Senza chiave non chiamiamo nessuno e non esplodiamo
    assert aa.suggest("Via Roma") == []


def test_short_query_does_not_call_provider(monkeypatch):
    called = []
    monkeypatch.setattr(aa.requests, "get", lambda *a, **k: called.append(1))
    assert aa.suggest("Vi") == []
    assert called == []


def test_suggestions_are_normalised(monkeypatch):
    payload = {"features": [_feature(
        formatted="Via Roma 12, 57100 Livorno, Italia",
        street="Via Roma", housenumber="12",
        postcode="57100", city="Livorno", county_code="LI", state_code="TOS",
        country="Italia", lat=43.54, lon=10.31,
    )]}
    monkeypatch.setattr(aa.requests, "get", lambda *a, **k: _Resp(payload))

    out = aa.suggest("Via Roma 12")
    assert out == [{
        "label": "Via Roma 12, 57100 Livorno, Italia",
        "street": "Via Roma 12",
        "postal_code": "57100",
        "city": "Livorno",
        "province": "LI",
        "country": "Italia",
        "lat": 43.54,
        "lon": 10.31,
    }]


def test_city_fallbacks_and_missing_housenumber(monkeypatch):
    """Geoapify usa town/village per i centri piccoli, e il civico puo'
    mancare: non deve finire uno spazio in coda alla via."""
    payload = {"features": [_feature(
        formatted="Via Lunga, 56010 Vicopisano, Italia",
        street="Via Lunga", postcode="56010", village="Vicopisano",
        county="Pisa", country="Italia",
    )]}
    monkeypatch.setattr(aa.requests, "get", lambda *a, **k: _Resp(payload))

    out = aa.suggest("Via Lunga")
    assert out[0]["street"] == "Via Lunga"
    assert out[0]["city"] == "Vicopisano"
    assert out[0]["province"] == "Pisa"


def test_region_code_is_never_used_as_province(monkeypatch):
    """state_code per l'Italia e' la regione ("TOS"): nel campo Provincia ci
    va la sigla della provincia, o niente."""
    payload = {"features": [_feature(
        formatted="Via Senza Provincia 1, Firenze", street="Via Senza Provincia",
        housenumber="1", city="Firenze", state_code="TOS", country="Italia",
    )]}
    monkeypatch.setattr(aa.requests, "get", lambda *a, **k: _Resp(payload))
    assert aa.suggest("Via Senza Provincia")[0]["province"] == ""


def test_results_without_label_are_dropped(monkeypatch):
    payload = {"features": [_feature(street="Via Senza Nome"), _feature(
        formatted="Via Vera 1, Pisa", street="Via Vera", housenumber="1",
    )]}
    monkeypatch.setattr(aa.requests, "get", lambda *a, **k: _Resp(payload))
    out = aa.suggest("Via")
    assert [s["label"] for s in out] == ["Via Vera 1, Pisa"]


def test_city_level_results_are_dropped(monkeypatch):
    """Un suggerimento di citta'/regione non ha una via: offrirlo nel campo
    "via e numero civico" fa finire "Viareggio, TOS, Italia" nell'indirizzo."""
    payload = {"features": [
        _feature(formatted="Viareggio, TOS, Italia", city="Viareggio",
                 postcode="55049", county_code="LU", country="Italia"),
        _feature(formatted="Via Fratti, 10, 55049 Viareggio LU, Italia",
                 street="Via Fratti", housenumber="10", postcode="55049",
                 city="Viareggio", county_code="LU", country="Italia"),
    ]}
    monkeypatch.setattr(aa.requests, "get", lambda *a, **k: _Resp(payload))

    out = aa.suggest("Viareggio")
    assert [s["street"] for s in out] == ["Via Fratti 10"]


def test_provider_down_degrades_to_empty(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("giu'")
    monkeypatch.setattr(aa.requests, "get", boom)
    # Nessuna eccezione: il compratore continua a scrivere l'indirizzo a mano
    assert aa.suggest("Via Roma") == []


def test_country_filter_is_configurable(monkeypatch):
    seen = {}

    def fake_get(url, params=None, timeout=None):
        seen.update(params or {})
        return _Resp({"features": []})

    monkeypatch.setattr(aa.requests, "get", fake_get)
    aa.suggest("Rue de Rivoli")
    assert seen["filter"] == "countrycode:it"

    monkeypatch.setenv("ADDRESS_COUNTRY_CODES", "it, fr")
    aa.suggest("Rue de Rivoli")
    assert seen["filter"] == "countrycode:it,fr"
