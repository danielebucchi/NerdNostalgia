"""
Client Stripe Checkout (pagamento con carta).

Flusso: dall'ordine PENDING creiamo una Checkout Session (pagina di pagamento
ospitata da Stripe); alla conferma, Stripe chiama il nostro webhook che marca
l'ordine PAID. Le chiavi vivono in env (in prod dal vault). Si parte in test
mode (chiavi sk_test_...).

Env:
  STRIPE_SECRET_KEY       sk_test_... / sk_live_...
  STRIPE_WEBHOOK_SECRET   whsec_... (per verificare la firma del webhook)
  SITE_PUBLIC_URL         base per success/cancel URL (riusa quella esistente)
"""
import logging
import os
from decimal import Decimal
from typing import Any, Optional

import stripe

LOGGER = logging.getLogger("stripe_client")


class StripeError(Exception):
    pass


def _secret() -> str:
    return (os.getenv("STRIPE_SECRET_KEY") or "").strip()


def _webhook_secret() -> str:
    return (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()


def _site_url() -> str:
    return (os.getenv("SITE_PUBLIC_URL") or "http://localhost:3737").rstrip("/")


def is_configured() -> bool:
    return bool(_secret())


def is_test_mode() -> bool:
    return _secret().startswith("sk_test_")


def _cents(amount: Decimal) -> int:
    return int((Decimal(amount) * 100).quantize(Decimal("1")))


def create_checkout_session(order) -> Any:
    """Crea una Checkout Session per un ordine PENDING. Ritorna l'oggetto
    Session (usiamo .id e .url). Le righe sono gli OrderItem + la spedizione
    come voce separata. `order_id` va nei metadata per ritrovarlo nel webhook."""
    if not is_configured():
        raise StripeError("Stripe non configurato: manca STRIPE_SECRET_KEY")
    stripe.api_key = _secret()

    line_items = []
    for it in order.items:
        line_items.append({
            "quantity": int(it.quantity or 1),
            "price_data": {
                "currency": (order.currency or "EUR").lower(),
                "unit_amount": _cents(it.price_snapshot),
                "product_data": {"name": (it.title_snapshot or "Articolo")[:250]},
            },
        })
    if order.shipping_total and Decimal(order.shipping_total) > 0:
        line_items.append({
            "quantity": 1,
            "price_data": {
                "currency": (order.currency or "EUR").lower(),
                "unit_amount": _cents(order.shipping_total),
                "product_data": {"name": "Spedizione"},
            },
        })

    site = _site_url()
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=line_items,
            customer_email=order.buyer_email or None,
            client_reference_id=str(order.id),
            metadata={"order_id": str(order.id)},
            success_url=f"{site}/ordine/grazie?order={order.id}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{site}/carrello?pagamento=annullato",
        )
    except stripe.StripeError as exc:  # noqa
        raise StripeError(f"Creazione sessione Stripe fallita: {exc}") from exc
    return session


def construct_event(payload: bytes, sig_header: str) -> Any:
    """Verifica la firma del webhook e restituisce l'evento. Solleva
    StripeError se la firma non e' valida (o manca il webhook secret)."""
    secret = _webhook_secret()
    if not secret:
        raise StripeError("STRIPE_WEBHOOK_SECRET non configurato")
    try:
        return stripe.Webhook.construct_event(payload, sig_header, secret)
    except (ValueError, stripe.SignatureVerificationError) as exc:  # noqa
        raise StripeError(f"Firma webhook non valida: {exc}") from exc
