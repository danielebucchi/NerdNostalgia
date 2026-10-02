"""Unit: l'invito a registrarsi nella conferma d'ordine.

L'invito e' utile solo a chi un profilo non ce l'ha: proporlo a un cliente
gia' registrato lo farebbe sentire non riconosciuto, proprio nel messaggio
che dovrebbe dirgli "ti ho visto, ho il tuo ordine".
"""
import types

import pytest

from utils import email as E


def _ordine(user_id):
    item = types.SimpleNamespace(
        title_snapshot="Pokemon Charizard",
        quantity=1,
        price_snapshot=12.50,
        article_id=234,
    )
    return types.SimpleNamespace(
        id=99,
        buyer_name="Mario Rossi",
        buyer_email="mario@example.it",
        items=[item],
        subtotal=12.50,
        shipping_total=6.21,
        grand_total=18.71,
        insured=False,
        inpost_point_id=None,
        inpost_point_name=None,
        ship_street="Via Alberto Profeti 271",
        ship_city="Cascina",
        ship_postal_code="56021",
        ship_province="PI",
        user_id=user_id,
    )


@pytest.fixture
def inviata(monkeypatch):
    """Cattura l'email invece di spedirla davvero."""
    catturate: list[dict] = []
    monkeypatch.setattr(
        E, "send_email", lambda **kw: (catturate.append(kw), True)[1]
    )
    monkeypatch.setattr(
        E,
        "_config",
        lambda: {"enabled": True, "to_admin": "admin@example.it"},
    )
    monkeypatch.setattr(E, "_site_url", lambda: "https://nerdnostalgia.store")
    return catturate


def _corpi(catturate):
    assert len(catturate) == 1
    kw = catturate[0]
    return " ".join(v for v in kw.values() if isinstance(v, str))


def test_ospite_riceve_invito_a_registrarsi(inviata):
    E.send_order_confirmation(_ordine(user_id=None))

    corpo = _corpi(inviata)
    assert "https://nerdnostalgia.store/registrati" in corpo
    assert "Vuoi seguire la spedizione" in corpo


def test_cliente_registrato_non_riceve_invito(inviata):
    E.send_order_confirmation(_ordine(user_id=7))

    corpo = _corpi(inviata)
    assert "/registrati" not in corpo
