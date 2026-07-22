"""
Client Vinted Pro Integrations API (VPI) — API UFFICIALE per venditori Pro.

Sostituisce lo scraping Playwright (fragile, gira solo dal Mac per il blocco
Cloudflare): questa è una REST vera → funziona dal datacenter Contabo.

Auth: firma HMAC-SHA256 (niente OAuth). Dal Vinted Pro Integrations Portal si
ottiene un token nel formato "{access_key},{signing_key}".
  - header X-Vpi-Access-Key: access key
  - header X-Vpi-Hmac-Sha256: "t={ts},v1={hex}"
  - stringa firmata (canonical), unita da '.':
        {timestamp}.{METHOD}.{path+query}.{access_key}.{body}
    body = corpo grezzo inviato (stringa vuota se assente).

Env:
  VINTED_PRO_ENV          sandbox | production (default sandbox)
  VINTED_PRO_ACCESS_KEY   access key dal portale
  VINTED_PRO_SIGNING_KEY  signing key dal portale

NB: l'accesso è su allowlist (domanda dal portale). Finché non si è approvati
le chiamate falliscono lato Vinted: l'impianto è pronto, il test end-to-end
arriva con le credenziali sandbox.
"""
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests

LOGGER = logging.getLogger("vinted_pro")

TIMEOUT = 30


class VintedProError(Exception):
    def __init__(self, message: str, status: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


def _env() -> str:
    return (os.getenv("VINTED_PRO_ENV") or "sandbox").strip().lower()


def is_sandbox() -> bool:
    return _env() != "production"


def _base_url() -> str:
    return (
        "https://pro.svc.vinted.com"
        if not is_sandbox()
        else "https://pro-public-sandbox.svc.vinted.com"
    )


def _access_key() -> str:
    return (os.getenv("VINTED_PRO_ACCESS_KEY") or "").strip()


def _signing_key() -> str:
    return (os.getenv("VINTED_PRO_SIGNING_KEY") or "").strip()


def is_configured() -> bool:
    return bool(_access_key() and _signing_key())


def _sign(timestamp: int, method: str, path_with_query: str, body: str) -> str:
    """HMAC-SHA256 (hex) del canonical string, come da doc VPI."""
    canonical = f"{timestamp}.{method.upper()}.{path_with_query}.{_access_key()}.{body}"
    return hmac.new(
        _signing_key().encode(), canonical.encode(), hashlib.sha256
    ).hexdigest()


def _request(method: str, path: str, *, params: Optional[dict] = None, body: Any = None) -> Any:
    if not is_configured():
        raise VintedProError("Vinted Pro non configurato: mancano access/signing key")

    # path+query firmato deve combaciare byte-per-byte con quello inviato
    query = ""
    if params:
        # ordine stabile per riproducibilità della firma
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    path_with_query = f"{path}?{query}" if query else path

    # il body firmato deve essere identico a quello inviato → serializzo 1 volta
    raw_body = "" if body is None else json.dumps(body, separators=(",", ":"), ensure_ascii=False)

    ts = int(time.time())
    signature = _sign(ts, method, path_with_query, raw_body)
    headers = {
        "X-Vpi-Access-Key": _access_key(),
        "X-Vpi-Hmac-Sha256": f"t={ts},v1={signature}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"

    url = f"{_base_url()}{path_with_query}"
    try:
        resp = requests.request(
            method, url, headers=headers,
            data=raw_body.encode() if body is not None else None,
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise VintedProError(f"Rete/timeout verso Vinted Pro: {exc}") from exc
    if resp.status_code in (401, 403):
        raise VintedProError(
            f"Auth Vinted Pro rifiutata ({resp.status_code}): firma o allowlist",
            resp.status_code, _safe_body(resp),
        )
    if resp.status_code >= 400:
        raise VintedProError(f"Vinted Pro {resp.status_code} su {path}", resp.status_code, _safe_body(resp))
    if not resp.content:
        return None
    try:
        return resp.json()
    except ValueError:
        return resp.text


def _safe_body(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return resp.text[:500]


# ── Wrapper endpoint (paths /api/v1/*, da confermare in sandbox) ────

def get_ontologies() -> Any:
    """Tassonomia Vinted (categorie/brand/condizioni) per mappare gli item."""
    return _request("GET", "/api/v1/ontologies")


def price_suggestions(body: dict) -> Any:
    return _request("POST", "/api/v1/items/price_suggestions", body=body)


def create_items(items: List[dict]) -> Any:
    return _request("POST", "/api/v1/items", body={"items": items})


def get_items(params: Optional[dict] = None) -> Any:
    return _request("GET", "/api/v1/items", params=params)


def get_item_status(params: Optional[dict] = None) -> Any:
    return _request("GET", "/api/v1/items/status", params=params)


def update_items(items: List[dict]) -> Any:
    return _request("PUT", "/api/v1/items", body={"items": items})


def validate_items(items: List[dict]) -> Any:
    return _request("POST", "/api/v1/items/validate", body={"items": items})


def delete_items(ids: List[str]) -> Any:
    return _request("POST", "/api/v1/items/delete", body={"ids": ids})


def get_orders(params: Optional[dict] = None) -> Any:
    return _request("GET", "/api/v1/orders", params=params)


def get_order(order_id: str) -> Any:
    return _request("GET", f"/api/v1/orders/{order_id}")


def get_order_shipment_label(order_id: str) -> Any:
    return _request("GET", f"/api/v1/orders/{order_id}/shipment/label")


def get_webhooks() -> Any:
    return _request("GET", "/api/v1/webhooks")


def create_webhook(body: dict) -> Any:
    return _request("POST", "/api/v1/webhooks", body=body)
