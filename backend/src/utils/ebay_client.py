"""
Client eBay Sell API (Inventory + Account + Taxonomy).

A differenza di CardTrader (JWT statico), eBay usa OAuth 2.0:
  - credenziali app: EBAY_CLIENT_ID (App ID) + EBAY_CLIENT_SECRET (Cert ID);
  - consenso utente una-tantum → refresh_token (dura ~18 mesi) salvato in
    EBAY_REFRESH_TOKEN; da questo si rinnovano gli access token (~2h),
    cachati in memoria.

EBAY_ENV = sandbox | production (default sandbox: si parte sempre in sandbox).
EBAY_MARKETPLACE_ID = mercato di pubblicazione (default EBAY_IT).

Il flusso di consenso (una volta sola):
  1. GET /api/ebay/consent-url → apri l'URL, accetti col tuo account eBay;
  2. eBay redirige al RuName con ?code=... ;
  3. POST /api/ebay/oauth-exchange {code} → ottieni il refresh_token da
     mettere in EBAY_REFRESH_TOKEN (vault).
"""
import base64
import logging
import os
import time
import urllib.parse
from typing import Any, Dict, List, Optional

import requests

LOGGER = logging.getLogger("ebay")

TIMEOUT = 30

# Scope minimi per creare/pubblicare inserzioni e leggere le business policy.
SCOPES = [
    "https://api.ebay.com/oauth/api_scope",
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.account",
]


class EbayError(Exception):
    def __init__(self, message: str, status: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


def _env() -> str:
    return (os.getenv("EBAY_ENV") or "sandbox").strip().lower()


def is_sandbox() -> bool:
    return _env() != "production"


def _api_base() -> str:
    return "https://api.sandbox.ebay.com" if is_sandbox() else "https://api.ebay.com"


def _auth_host() -> str:
    return "auth.sandbox.ebay.com" if is_sandbox() else "auth.ebay.com"


def _token_url() -> str:
    return f"{_api_base()}/identity/v1/oauth2/token"


def _client_id() -> str:
    return (os.getenv("EBAY_CLIENT_ID") or "").strip()


def _client_secret() -> str:
    return (os.getenv("EBAY_CLIENT_SECRET") or "").strip()


def _runame() -> str:
    return (os.getenv("EBAY_REDIRECT_RUNAME") or "").strip()


def _refresh_token() -> str:
    return (os.getenv("EBAY_REFRESH_TOKEN") or "").strip()


def marketplace_id() -> str:
    return (os.getenv("EBAY_MARKETPLACE_ID") or "EBAY_IT").strip()


def is_configured() -> bool:
    """Pronto per chiamate API: servono credenziali app + refresh token."""
    return bool(_client_id() and _client_secret() and _refresh_token())


def can_start_consent() -> bool:
    """Pronto per avviare il consenso (non serve ancora il refresh token)."""
    return bool(_client_id() and _client_secret() and _runame())


def _basic_auth() -> str:
    raw = f"{_client_id()}:{_client_secret()}".encode()
    return "Basic " + base64.b64encode(raw).decode()


# ── OAuth ──────────────────────────────────────────────────────────

def consent_url(scopes: Optional[List[str]] = None) -> str:
    """URL di consenso da aprire nel browser (login col tuo account eBay)."""
    if not can_start_consent():
        raise EbayError("Config incompleta: servono EBAY_CLIENT_ID/SECRET/REDIRECT_RUNAME")
    params = {
        "client_id": _client_id(),
        "redirect_uri": _runame(),
        "response_type": "code",
        "scope": " ".join(scopes or SCOPES),
    }
    return f"https://{_auth_host()}/oauth2/authorize?" + urllib.parse.urlencode(params)


def exchange_code(code: str) -> Dict[str, Any]:
    """Scambia il `code` del redirect per access+refresh token.
    Il refresh_token restituito va salvato in EBAY_REFRESH_TOKEN (vault)."""
    if not can_start_consent():
        raise EbayError("Config incompleta per lo scambio del code")
    resp = requests.post(
        _token_url(),
        headers={"Authorization": _basic_auth(), "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": _runame()},
        timeout=TIMEOUT,
    )
    if resp.status_code >= 400:
        raise EbayError(f"Scambio code fallito ({resp.status_code})", resp.status_code, _safe_body(resp))
    return resp.json()


# Access token cachato in memoria (rinnovato dal refresh token)
_TOKEN: Dict[str, Any] = {"value": None, "exp": 0.0}


def _access_token() -> str:
    if not is_configured():
        raise EbayError("eBay non configurato: mancano credenziali o refresh token")
    now = time.time()
    if _TOKEN["value"] and now < _TOKEN["exp"] - 60:  # margine 60s
        return _TOKEN["value"]
    resp = requests.post(
        _token_url(),
        headers={"Authorization": _basic_auth(), "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "refresh_token", "refresh_token": _refresh_token(), "scope": " ".join(SCOPES)},
        timeout=TIMEOUT,
    )
    if resp.status_code >= 400:
        raise EbayError(f"Refresh token fallito ({resp.status_code})", resp.status_code, _safe_body(resp))
    data = resp.json()
    _TOKEN["value"] = data["access_token"]
    _TOKEN["exp"] = now + int(data.get("expires_in", 7200))
    return _TOKEN["value"]


def _safe_body(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return resp.text[:500]


def _request(
    method: str,
    path: str,
    *,
    params: Optional[dict] = None,
    json: Optional[dict] = None,
    extra_headers: Optional[dict] = None,
) -> Any:
    url = f"{_api_base()}{path}"
    headers = {
        "Authorization": f"Bearer {_access_token()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        # Lingua contenuti + mercato: molte Sell API vogliono questi header.
        "Content-Language": "it-IT",
        "X-EBAY-C-MARKETPLACE-ID": marketplace_id(),
    }
    if extra_headers:
        headers.update(extra_headers)
    try:
        resp = requests.request(method, url, headers=headers, params=params, json=json, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise EbayError(f"Rete/timeout verso eBay: {exc}") from exc
    if resp.status_code == 401:
        raise EbayError("Token eBay non valido/scaduto (401)", 401, _safe_body(resp))
    if resp.status_code >= 400:
        raise EbayError(f"eBay {resp.status_code} su {path}", resp.status_code, _safe_body(resp))
    if not resp.content:
        return None
    try:
        return resp.json()
    except ValueError:
        return resp.text


# ── Account (business policies + location) ─────────────────────────

def fulfillment_policies() -> Any:
    return _request("GET", "/sell/account/v1/fulfillment_policy",
                    params={"marketplace_id": marketplace_id()})


def payment_policies() -> Any:
    return _request("GET", "/sell/account/v1/payment_policy",
                    params={"marketplace_id": marketplace_id()})


def return_policies() -> Any:
    return _request("GET", "/sell/account/v1/return_policy",
                    params={"marketplace_id": marketplace_id()})


def inventory_locations() -> Any:
    return _request("GET", "/sell/inventory/v1/location")


# ── Taxonomy (categorie + item specifics) ──────────────────────────

def default_category_tree_id() -> str:
    data = _request("GET", "/commerce/taxonomy/v1/get_default_category_tree_id",
                    params={"marketplace_id": marketplace_id()})
    return (data or {}).get("categoryTreeId", "")


def category_suggestions(tree_id: str, query: str) -> Any:
    return _request("GET", f"/commerce/taxonomy/v1/category_tree/{tree_id}/get_category_suggestions",
                    params={"q": query})


def item_aspects_for_category(tree_id: str, category_id: str) -> Any:
    return _request("GET", f"/commerce/taxonomy/v1/category_tree/{tree_id}/get_item_aspects_for_category",
                    params={"category_id": category_id})


# ── Inventory + Offer + Publish ────────────────────────────────────

def put_inventory_item(sku: str, body: dict) -> Any:
    """PUT /inventory_item/{sku} — crea/sostituisce l'articolo a catalogo."""
    return _request("PUT", f"/sell/inventory/v1/inventory_item/{urllib.parse.quote(sku)}", json=body)


def delete_inventory_item(sku: str) -> Any:
    return _request("DELETE", f"/sell/inventory/v1/inventory_item/{urllib.parse.quote(sku)}")


def get_offers(sku: str) -> Any:
    return _request("GET", "/sell/inventory/v1/offer", params={"sku": sku})


def create_offer(body: dict) -> Any:
    return _request("POST", "/sell/inventory/v1/offer", json=body)


def update_offer(offer_id: str, body: dict) -> Any:
    return _request("PUT", f"/sell/inventory/v1/offer/{offer_id}", json=body)


def publish_offer(offer_id: str) -> Any:
    return _request("POST", f"/sell/inventory/v1/offer/{offer_id}/publish")


def withdraw_offer(offer_id: str) -> Any:
    return _request("POST", f"/sell/inventory/v1/offer/{offer_id}/withdraw")


def delete_offer(offer_id: str) -> Any:
    return _request("DELETE", f"/sell/inventory/v1/offer/{offer_id}")


# ── Inserzioni con varianti (inventory item group) ─────────────────
#
# Piu' articoli (uno SKU ciascuno, con la sua offerta) sotto un'unica
# inserzione: il compratore sceglie la variante da un menu. Il gruppo dice
# per quale caratteristica variano; la pubblicazione e' del gruppo intero.

def get_inventory_item_group(key: str) -> Any:
    return _request("GET", f"/sell/inventory/v1/inventory_item_group/{urllib.parse.quote(key)}")


def put_inventory_item_group(key: str, body: dict) -> Any:
    """PUT /inventory_item_group/{key} — crea/sostituisce il gruppo."""
    return _request("PUT", f"/sell/inventory/v1/inventory_item_group/{urllib.parse.quote(key)}", json=body)


def delete_inventory_item_group(key: str) -> Any:
    """Cancella il gruppo (non gli articoli): gli SKU tornano liberi."""
    return _request("DELETE", f"/sell/inventory/v1/inventory_item_group/{urllib.parse.quote(key)}")


def publish_by_inventory_item_group(key: str) -> Any:
    """Pubblica (o riallinea) l'inserzione del gruppo; risponde col listingId."""
    return _request("POST", "/sell/inventory/v1/offer/publish_by_inventory_item_group",
                    json={"inventoryItemGroupKey": key, "marketplaceId": marketplace_id()})


def withdraw_by_inventory_item_group(key: str) -> Any:
    return _request("POST", "/sell/inventory/v1/offer/withdraw_by_inventory_item_group",
                    json={"inventoryItemGroupKey": key, "marketplaceId": marketplace_id()})


# ── Venduti (Marketplace Insights) ─────────────────────────────────
#
# L'unica fonte ufficiale dei prezzi di vendita conclusi. E' un'API ad
# accesso limitato: va chiesta a eBay per l'app (Application Growth
# Check), finche' non e' abilitata risponde 403. Usa un token
# APPLICAZIONE (client credentials), non quello del venditore: i venduti
# altrui non c'entrano col consenso del tuo account.

INSIGHTS_SCOPE = "https://api.ebay.com/oauth/api_scope/buy.marketplace.insights"

_APP_TOKENS: Dict[str, Dict[str, Any]] = {}


def has_app_credentials() -> bool:
    return bool(_client_id() and _client_secret())


def _app_token(scope: str) -> str:
    if not has_app_credentials():
        raise EbayError("eBay non configurato: mancano EBAY_CLIENT_ID/EBAY_CLIENT_SECRET")
    now = time.time()
    cached = _APP_TOKENS.get(scope)
    if cached and now < cached["exp"] - 60:
        return cached["value"]
    resp = requests.post(
        _token_url(),
        headers={"Authorization": _basic_auth(), "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials", "scope": scope},
        timeout=TIMEOUT,
    )
    if resp.status_code >= 400:
        raise EbayError(f"Token applicazione eBay negato ({resp.status_code})",
                        resp.status_code, _safe_body(resp))
    data = resp.json()
    _APP_TOKENS[scope] = {"value": data["access_token"],
                          "exp": now + int(data.get("expires_in", 7200))}
    return data["access_token"]


def sold_items_search(query: str, limit: int = 50, category_id: Optional[str] = None) -> List[dict]:
    """Vendite concluse negli ultimi 90 giorni che corrispondono alla
    ricerca. Ogni voce: title, lastSoldPrice{value,currency},
    lastSoldDate, itemWebUrl, totalSoldQuantity."""
    params: Dict[str, Any] = {"q": query, "limit": limit}
    if category_id:
        params["category_ids"] = category_id
    url = f"{_api_base()}/buy/marketplace_insights/v1_beta/item_sales/search"
    try:
        resp = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {_app_token(INSIGHTS_SCOPE)}",
                "X-EBAY-C-MARKETPLACE-ID": marketplace_id(),
                "Accept": "application/json",
            },
            params=params,
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise EbayError(f"Rete/timeout verso eBay: {exc}") from exc
    if resp.status_code == 403:
        raise EbayError(
            "Marketplace Insights non abilitata per questa app eBay: va richiesta "
            "a eBay. Nel frattempo inserisci i venduti a mano.",
            403, _safe_body(resp),
        )
    if resp.status_code >= 400:
        raise EbayError(f"eBay {resp.status_code} sui venduti", resp.status_code, _safe_body(resp))
    return (resp.json() or {}).get("itemSales") or []
