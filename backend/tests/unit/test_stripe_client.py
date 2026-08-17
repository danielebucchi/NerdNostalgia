"""Unit: Stripe Checkout client (cents, line items, config)."""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from utils import stripe_client as sc


def test_cents():
    assert sc._cents(Decimal("5.39")) == 539
    assert sc._cents(Decimal("214.90")) == 21490
    assert sc._cents(Decimal("0")) == 0


def test_not_configured(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    assert sc.is_configured() is False
    with pytest.raises(sc.StripeError):
        sc.create_checkout_session(SimpleNamespace())


def _fake_order():
    return SimpleNamespace(
        id=42,
        currency="EUR",
        buyer_email="mario@example.com",
        shipping_total=Decimal("5.00"),
        items=[
            SimpleNamespace(title_snapshot="Carta A", price_snapshot=Decimal("4.99"), quantity=1),
            SimpleNamespace(title_snapshot="Carta B", price_snapshot=Decimal("10.00"), quantity=2),
        ],
    )


def test_create_checkout_session_payload(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    monkeypatch.setenv("SITE_PUBLIC_URL", "https://nerdnostalgia.store")
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id="cs_test_1", url="https://checkout.stripe.com/x")

    monkeypatch.setattr(sc.stripe.checkout.Session, "create", staticmethod(fake_create))
    session = sc.create_checkout_session(_fake_order())

    assert session.id == "cs_test_1"
    li = captured["line_items"]
    assert len(li) == 3  # 2 articoli + spedizione
    assert li[0]["price_data"]["unit_amount"] == 499
    assert li[1]["price_data"]["unit_amount"] == 1000
    assert li[1]["quantity"] == 2
    assert li[2]["price_data"]["product_data"]["name"] == "Spedizione"
    assert captured["metadata"]["order_id"] == "42"
    assert captured["client_reference_id"] == "42"
    assert "session_id={CHECKOUT_SESSION_ID}" in captured["success_url"]
    assert captured["success_url"].startswith("https://nerdnostalgia.store/ordine/grazie")


def test_create_checkout_no_shipping(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    captured = {}
    monkeypatch.setattr(
        sc.stripe.checkout.Session, "create",
        staticmethod(lambda **kw: (captured.update(kw), SimpleNamespace(id="x", url="u"))[1]),
    )
    order = _fake_order()
    order.shipping_total = Decimal("0")
    sc.create_checkout_session(order)
    assert len(captured["line_items"]) == 2  # nessuna riga spedizione


def test_is_test_mode(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    assert sc.is_test_mode() is True
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_abc")
    assert sc.is_test_mode() is False
