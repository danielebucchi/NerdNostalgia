"""La conferma d'ordine non propone di registrarsi.

E' una comunicazione di servizio su un acquisto gia' pagato: infilarci
una proposta commerciale la trasforma in pubblicita', e chi aspetta la
conferma di quanto ha speso non deve leggere altro.

Il test resta a presidio: l'invito esiste ancora altrove (pagina di
ringraziamento e checkout) e sarebbe facile rimetterlo anche qui.
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
        E, "_config", lambda: {"enabled": True, "to_admin": "admin@example.it"}
    )
    monkeypatch.setattr(E, "_site_url", lambda: "https://nerdnostalgia.store")
    return catturate


def _corpi(catturate):
    assert len(catturate) == 1
    kw = catturate[0]
    return " ".join(v for v in kw.values() if isinstance(v, str))


@pytest.mark.parametrize("user_id", [None, 7])
def test_the_confirmation_never_invites_to_register(inviata, user_id):
    """Ne' all'ospite ne' a chi ha gia' un profilo."""
    E.send_order_confirmation(_ordine(user_id=user_id))

    corpo = _corpi(inviata)
    assert "/registrati" not in corpo
    assert "Crea il profilo" not in corpo
