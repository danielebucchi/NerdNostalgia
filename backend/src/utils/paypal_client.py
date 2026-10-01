"""
Client PayPal Orders v2 (bottoni ufficiali + popup).

Sostituisce il link paypal.me, che era solo una richiesta di denaro: non
diceva mai se il compratore avesse pagato, e l'ordine andava marcato PAID a
mano. Qui il pagamento si apre nella finestra PayPal, noi lo catturiamo
server-side e il webhook conferma l'incasso.

Flusso:
  1. il browser chiede /api/paypal/orders/{id} → qui creiamo l'ordine PayPal
     e restituiamo il suo id al bottone;
  2. il compratore approva nel popup PayPal;
  3. il browser chiama /capture → catturiamo l'incasso e marchiamo PAID;
  4. il webhook PAYMENT.CAPTURE.COMPLETED fa da rete di sicurezza se il
     browser muore fra l'approvazione e la cattura.

Env:
  PAYPAL_ENV            sandbox | live  (default sandbox: non si va in
                        produzione per distrazione)
  PAYPAL_CLIENT_ID      pubblico: finisce nell'URL dell'SDK nel browser
  PAYPAL_CLIENT_SECRET  segreto: resta qui
  PAYPAL_WEBHOOK_ID     id del webhook, serve a verificarne la firma
"""
import logging
import os
import time
from decimal import Decimal
from typing import Any, Dict, Optional

import requests

LOGGER = logging.getLogger("paypal")

TIMEOUT = 30
# Rinnoviamo il token un minuto prima della scadenza dichiarata.
_TOKEN: Dict[str, Any] = {"value": None, "exp": 0.0}


class PaypalError(Exception):
    def __init__(self, message: str, status: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


def _env() -> str:
    return (os.getenv("PAYPAL_ENV") or "sandbox").strip().lower()


def is_sandbox() -> bool:
    return _env() != "live"


def _api_base() -> str:
    return (
        "https://api-m.sandbox.paypal.com"
        if is_sandbox()
        else "https://api-m.paypal.com"
    )


def _client_id() -> str:
    return (os.getenv("PAYPAL_CLIENT_ID") or "").strip()


def _client_secret() -> str:
    return (os.getenv("PAYPAL_CLIENT_SECRET") or "").strip()


def _webhook_id() -> str:
    return (os.getenv("PAYPAL_WEBHOOK_ID") or "").strip()


def is_configured() -> bool:
    return bool(_client_id() and _client_secret())


def public_config() -> Dict[str, Any]:
    """Quel che il browser puo' sapere: il client id e' pubblico per progetto,
    il secret no."""
    return {
        "configured": is_configured(),
        "client_id": _client_id() if is_configured() else "",
        "sandbox": is_sandbox(),
        "webhook_ready": bool(_webhook_id()),
    }


def _access_token() -> str:
    """Token OAuth client-credentials, cachato in memoria finche' valido."""
    now = time.time()
    if _TOKEN["value"] and now < _TOKEN["exp"]:
        return _TOKEN["value"]
    if not is_configured():
        raise PaypalError("PayPal non configurato: mancano client id/secret")

    resp = requests.post(
        f"{_api_base()}/v1/oauth2/token",
        auth=(_client_id(), _client_secret()),
        data={"grant_type": "client_credentials"},
        headers={"Accept": "application/json"},
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        raise PaypalError(
            "Autenticazione PayPal fallita", resp.status_code, resp.text[:400]
        )
    payload = resp.json()
    _TOKEN["value"] = payload["access_token"]
    _TOKEN["exp"] = now + max(60, int(payload.get("expires_in", 3600)) - 60)
    return _TOKEN["value"]


def _request(method: str, path: str, **kwargs) -> Any:
    headers = kwargs.pop("headers", {})
    headers.setdefault("Authorization", f"Bearer {_access_token()}")
    headers.setdefault("Content-Type", "application/json")
    resp = requests.request(
        method, f"{_api_base()}{path}", headers=headers, timeout=TIMEOUT, **kwargs
    )
    if resp.status_code >= 400:
        raise PaypalError(
            f"PayPal {method} {path} ha risposto {resp.status_code}",
            resp.status_code,
            resp.text[:600],
        )
    return resp.json() if resp.content else {}


def _money(value) -> str:
    return f"{Decimal(value):.2f}"


def create_order(order, return_base_url: str) -> Dict[str, Any]:
    """Crea l'ordine PayPal a partire dal nostro. `reference_id` porta il
    nostro id, cosi' il webhook sa a quale ordine appartiene l'incasso."""
    items = []
    for it in order.items:
        items.append({
            "name": (it.title_snapshot or "Articolo")[:127],
            "quantity": str(int(it.quantity or 1)),
            "unit_amount": {
                "currency_code": order.currency or "EUR",
                "value": _money(it.price_snapshot),
            },
        })

    currency = order.currency or "EUR"
    item_total = sum(
        Decimal(it.price_snapshot) * int(it.quantity or 1) for it in order.items
    )
    body = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": str(order.id),
            "custom_id": str(order.id),
            "invoice_id": f"NN-{order.id}",
            "description": f"Ordine Nerd.Nostalgia #{order.id}"[:127],
            "amount": {
                "currency_code": currency,
                "value": _money(order.grand_total),
                "breakdown": {
                    "item_total": {
                        "currency_code": currency,
                        "value": _money(item_total),
                    },
                    "shipping": {
                        "currency_code": currency,
                        "value": _money(order.shipping_total),
                    },
                },
            },
            "items": items,
        }],
        "application_context": {
            "brand_name": "Nerd.Nostalgia",
            "locale": "it-IT",
            "shipping_preference": "NO_SHIPPING",  # l'indirizzo l'abbiamo gia'
            "user_action": "PAY_NOW",
            "return_url": f"{return_base_url}/ordine/grazie?order={order.id}",
            "cancel_url": f"{return_base_url}/carrello?pagamento=annullato",
        },
    }
    return _request("POST", "/v2/checkout/orders", json=body)


def capture_order(paypal_order_id: str) -> Dict[str, Any]:
    """Incassa un ordine approvato dal compratore."""
    return _request("POST", f"/v2/checkout/orders/{paypal_order_id}/capture")


def capture_id_from(capture_payload: Dict[str, Any]) -> Optional[str]:
    """Pesca l'id della cattura dalla risposta, per riconciliare e rimborsare."""
    try:
        units = capture_payload.get("purchase_units") or []
        captures = (units[0].get("payments") or {}).get("captures") or []
        return captures[0].get("id")
    except (IndexError, AttributeError, KeyError):
        return None


def is_completed(capture_payload: Dict[str, Any]) -> bool:
    return (capture_payload.get("status") or "").upper() == "COMPLETED"


def verify_webhook(headers: Dict[str, str], raw_body: str) -> bool:
    """Verifica la firma del webhook chiedendolo a PayPal.

    Senza PAYPAL_WEBHOOK_ID non possiamo verificare: rispondiamo False e
    l'endpoint rifiuta. Meglio ignorare una notifica che fidarsi di chiunque
    sappia l'URL.
    """
    webhook_id = _webhook_id()
    if not webhook_id:
        LOGGER.warning("PAYPAL_WEBHOOK_ID non configurato: webhook rifiutato")
        return False

    def head(name: str) -> str:
        return headers.get(name) or headers.get(name.lower()) or ""

    body = {
        "auth_algo": head("Paypal-Auth-Algo"),
        "cert_url": head("Paypal-Cert-Url"),
        "transmission_id": head("Paypal-Transmission-Id"),
        "transmission_sig": head("Paypal-Transmission-Sig"),
        "transmission_time": head("Paypal-Transmission-Time"),
        "webhook_id": webhook_id,
        "webhook_event": __import__("json").loads(raw_body),
    }
    if not all([body["transmission_id"], body["transmission_sig"], body["cert_url"]]):
        return False
    try:
        out = _request(
            "POST", "/v1/notifications/verify-webhook-signature", json=body
        )
    except PaypalError as exc:
        LOGGER.warning("Verifica firma webhook fallita: %s", exc)
        return False
    return (out.get("verification_status") or "").upper() == "SUCCESS"
