"""Il testo degli sconosciuti non deve diventare HTML nelle mie email.

Senza escape, chi scrive dal form contatti chiude il <pre> e infila nel
messaggio che arriva all'admin un link suo: un'email di phishing partita
davvero dal sito, che supera i controlli antispam perche' il mittente e'
autentico. Vale anche per il nome e l'indirizzo scritti in un ordine.
"""
import types

import pytest

from utils import email as E


ATTACCO = (
    '</pre><p>Il tuo account e\' sospeso: '
    '<a href="http://cattivo.example/login">verifica qui</a></p><pre>'
)


@pytest.fixture
def inviata(monkeypatch):
    catturate: list[dict] = []
    monkeypatch.setattr(E, "send_email", lambda **kw: (catturate.append(kw), True)[1])
    monkeypatch.setattr(E, "_config", lambda: {"enabled": True, "to_admin": "admin@test.it"})
    monkeypatch.setattr(E, "_site_url", lambda: "https://nerdnostalgia.store")
    return catturate


def _html(catturate) -> str:
    assert len(catturate) == 1
    return catturate[0]["html_body"]


# --- form contatti: il vettore piu' esposto -------------------------------


def test_a_message_cannot_inject_a_link(inviata):
    inquiry = types.SimpleNamespace(
        id=1, name="Mario Rossi", email="mario@example.com",
        phone=None, subject=None, message=ATTACCO,
    )

    E.send_inquiry_notification(inquiry)

    html = _html(inviata)
    assert "<a href=\"http://cattivo.example/login\">" not in html
    assert "&lt;a href=" in html


def test_the_sender_name_cannot_inject_html(inviata):
    inquiry = types.SimpleNamespace(
        id=1, name='<img src=x onerror="alert(1)">', email="m@e.it",
        phone=None, subject=None, message="ciao",
    )

    E.send_inquiry_notification(inquiry)

    assert "<img src=x" not in _html(inviata)


def test_the_subject_cannot_inject_html(inviata):
    inquiry = types.SimpleNamespace(
        id=1, name="Mario", email="m@e.it", phone=None,
        subject="<script>cattivo()</script>", message="ciao",
    )

    E.send_inquiry_notification(inquiry)

    assert "<script>" not in _html(inviata)


# --- ordini: nome e indirizzo li scrive il compratore ---------------------


def _ordine(**extra):
    it = types.SimpleNamespace(title_snapshot="Charizard", quantity=1,
                               price_snapshot=12.50, article_id=1)
    base = dict(
        id=7, buyer_name="Mario Rossi", buyer_email="m@e.it", buyer_phone=None,
        items=[it], subtotal=12.50, shipping_total=6.21, grand_total=18.71,
        insured=False, insurance_fee=0, currency="EUR", notes=None,
        inpost_point_id=None, inpost_point_name=None, user_id=None,
        ship_street="Via Roma 1", ship_city="Cascina", ship_postal_code="56021",
        ship_province="PI", ship_country="Italia",
    )
    base.update(extra)
    return types.SimpleNamespace(**base)


def test_the_buyer_name_cannot_inject_html_in_my_notification(inviata):
    E.send_order_notification(_ordine(buyer_name=ATTACCO))

    assert 'href="http://cattivo.example/login"' not in _html(inviata)


def test_the_address_cannot_inject_html(inviata):
    E.send_order_notification(_ordine(ship_street='<script>x()</script>'))

    assert "<script>" not in _html(inviata)


def test_the_notes_cannot_inject_html(inviata):
    E.send_order_notification(_ordine(notes=ATTACCO))

    assert 'href="http://cattivo.example/login"' not in _html(inviata)


def test_the_article_title_cannot_inject_html(inviata):
    """I titoli arrivano anche dalle sincronizzazioni con Vinted ed eBay:
    non sono testo scritto da noi."""
    it = types.SimpleNamespace(title_snapshot='<script>x()</script>',
                               quantity=1, price_snapshot=1.0, article_id=1)

    E.send_order_confirmation(_ordine(items=[it]))

    assert "<script>" not in _html(inviata)


# --- il testo semplice non deve peggiorare --------------------------------


def test_plain_text_keeps_the_apostrophes(inviata):
    """L'escape va solo nell'HTML: nel testo semplice un apostrofo
    diventerebbe &#x27; e si leggerebbe peggio di prima."""
    inquiry = types.SimpleNamespace(
        id=1, name="Mario", email="m@e.it", phone=None, subject=None,
        message="Vorrei sapere se l'articolo e' ancora disponibile",
    )

    E.send_inquiry_notification(inquiry)

    assert "l'articolo" in inviata[0]["text_body"]
    assert "&#x27;" not in inviata[0]["text_body"]
