"""
Client CardTrader API v2 (https://api.cardtrader.com).

Auth: Bearer JWT via env CARDTRADER_JWT (in prod dal vault garganacl).
A differenza di Vinted, e' una vera REST API pensata per l'uso
programmatico → dovrebbe funzionare anche dal datacenter (Contabo),
mentre lo scraping Vinted e' bloccato da Cloudflare.

Modello: i prodotti si pubblicano contro un `blueprint_id` (voce di
catalogo di una carta in una espansione). Vedi cardtrader.py per gli
endpoint admin.
"""
import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests

LOGGER = logging.getLogger("cardtrader")

BASE_URL = "https://api.cardtrader.com/api/v2"
TIMEOUT = 25


class CardTraderError(Exception):
    """Errore chiamata CardTrader (con status e corpo se disponibili)."""

    def __init__(self, message: str, status: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


def _jwt() -> str:
    return os.getenv("CARDTRADER_JWT", "").strip()


def is_configured() -> bool:
    return bool(_jwt())


def _headers() -> Dict[str, str]:
    token = _jwt()
    if not token:
        raise CardTraderError("CARDTRADER_JWT non configurato")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, *, params=None, json=None) -> Any:
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.request(
            method, url, headers=_headers(), params=params, json=json, timeout=TIMEOUT
        )
    except requests.RequestException as exc:
        raise CardTraderError(f"Rete/timeout verso CardTrader: {exc}") from exc
    if resp.status_code == 401:
        raise CardTraderError("JWT non valido o scaduto (401)", status=401)
    if resp.status_code >= 400:
        try:
            body = resp.json()
        except ValueError:
            body = resp.text[:500]
        raise CardTraderError(
            f"CardTrader {resp.status_code} su {path}", status=resp.status_code, body=body
        )
    if not resp.content:
        return None
    try:
        return resp.json()
    except ValueError:
        return resp.text


# ── Lettura catalogo ───────────────────────────────────────────────

def info() -> Any:
    """Dati dell'app/account collegato al JWT (prova connessione)."""
    return _request("GET", "/info")


def games() -> List[dict]:
    data = _request("GET", "/games")
    # L'API puo' restituire {"array":[...]} o lista diretta
    if isinstance(data, dict):
        return data.get("array", data.get("games", []))
    return data or []


def expansions() -> List[dict]:
    return _request("GET", "/expansions", params={"page": 1, "limit": 4000000}) or []


def blueprints(expansion_id: int) -> List[dict]:
    """Tutti i blueprint di una espansione (per abbinare la carta)."""
    return _request("GET", "/blueprints/export", params={"expansion_id": expansion_id}) or []


# Cache in-memory: espansioni ed export blueprint cambiano di rado, ma il
# match automatico li interroga spesso → TTL 1h per non martellare l'API.
_CACHE: Dict[str, Any] = {}


def _cached(key: str, ttl: int, producer):
    entry = _CACHE.get(key)
    if entry and (time.time() - entry[0]) < ttl:
        return entry[1]
    val = producer()
    _CACHE[key] = (time.time(), val)
    return val


def expansions_cached(ttl: int = 3600) -> List[dict]:
    return _cached("expansions", ttl, expansions)


def blueprints_cached(expansion_id: int, ttl: int = 3600) -> List[dict]:
    return _cached(f"bp:{expansion_id}", ttl, lambda: blueprints(expansion_id))


def blueprint_editable_properties(blueprint_id: int) -> List[dict]:
    """editable_properties del blueprint (condition, *_language, *_reverse,
    first_edition, ...). Il singolo GET /blueprints/{id} non le espone, ma
    l'export per espansione si': risalgo l'expansion_id e le pesco da li'."""
    def _load():
        bp = _request("GET", f"/blueprints/{blueprint_id}") or {}
        exp_id = bp.get("expansion_id") if isinstance(bp, dict) else None
        if not exp_id:
            return []
        for b in blueprints_cached(exp_id):
            if b.get("id") == blueprint_id:
                return b.get("editable_properties") or []
        return []
    return _cached(f"editprops:{blueprint_id}", 3600, _load)


def build_product_properties(
    blueprint_id: int,
    *,
    condition: str = "Near Mint",
    language: Optional[str] = None,
    reverse: bool = False,
    first_edition: bool = False,
) -> Dict[str, Any]:
    """Costruisce il dict `properties` per POST /products in base alle
    editable_properties del blueprint (i nomi property variano per gioco:
    pokemon_language vs mtg_language, ecc.). Invia solo cio' che il blueprint
    supporta davvero (es. first_edition esiste solo sui set vecchi)."""
    editable = blueprint_editable_properties(blueprint_id)
    names = {e.get("name") for e in editable}
    props: Dict[str, Any] = {}
    if "condition" in names or not names:
        props["condition"] = condition
    lang_name = next((n for n in names if isinstance(n, str) and n.endswith("_language")), None)
    if lang_name and language:
        props[lang_name] = language
    rev_name = next((n for n in names if isinstance(n, str) and n.endswith("_reverse")), None)
    if rev_name and reverse:
        props[rev_name] = True
    if "first_edition" in names and first_edition:
        props["first_edition"] = True
    return props


def _match_filters(
    props: Any,
    *,
    condition: Optional[str] = None,
    language: Optional[str] = None,
    reverse: Optional[bool] = None,
    first_edition: Optional[bool] = None,
) -> bool:
    """True se il properties_hash di un'inserzione soddisfa i filtri dati
    (quelli None sono ignorati). Chiavi lingua/reverse variano per gioco →
    match sul suffisso. Reverse/first_edition assenti = trattati come False."""
    if not isinstance(props, dict):
        return False
    if condition and str(props.get("condition", "")).strip().lower() != condition.strip().lower():
        return False
    if language:
        lang_key = next((k for k in props if isinstance(k, str) and k.endswith("_language")), None)
        if not lang_key or str(props.get(lang_key, "")).lower() != language.lower():
            return False
    if reverse is not None:
        rev_key = next((k for k in props if isinstance(k, str) and k.endswith("_reverse")), None)
        if bool(props.get(rev_key)) != bool(reverse):
            return False
    if first_edition is not None:
        if bool(props.get("first_edition")) != bool(first_edition):
            return False
    return True


def _price_to_cents(price: Any) -> Optional[int]:
    """Normalizza il prezzo di un'inserzione marketplace in centesimi.
    L'API usa di solito {"cents": 400, "currency":"EUR"}; tolleriamo anche
    un numero decimale in euro."""
    if isinstance(price, dict):
        c = price.get("cents")
        return int(c) if c is not None else None
    if isinstance(price, (int, float)):
        return int(round(float(price) * 100))
    return None


def marketplace_products(blueprint_id: int) -> List[dict]:
    """Inserzioni attive per un blueprint. La risposta e' un dict keyed per
    blueprint_id → lista prodotti; normalizziamo a lista piatta."""
    data = _request(
        "GET", "/marketplace/products", params={"blueprint_id": blueprint_id}
    )
    if isinstance(data, dict):
        out: List[dict] = []
        for v in data.values():
            if isinstance(v, list):
                out.extend(v)
        return out
    return data or []


def suggested_price_cents(
    blueprint_id: int,
    position: int = 4,
    *,
    condition: Optional[str] = None,
    language: Optional[str] = None,
    reverse: Optional[bool] = None,
    first_edition: Optional[bool] = None,
) -> Optional[dict]:
    """Prezzo consigliato = il N-esimo piu' basso (default 4°) tra le
    inserzioni COMPARABILI del blueprint. I filtri (condizione, lingua,
    reverse, prima edizione) restringono alle inserzioni con le stesse
    caratteristiche: cosi' il "4° piu' basso" e' quello giusto per la carta
    che stai vendendo, non un mix di condizioni/lingue diverse.
    Se ce ne sono meno di N, prende l'ultimo disponibile. Ritorna
    {cents, position, total, all_cents, filtered} o None se nessuna inserzione."""
    products = marketplace_products(blueprint_id)
    # Le carte gradate (slab PSA/BGS) hanno prezzi non comparabili con la carta
    # sciolta → mai usate come riferimento per il "4° piu' basso".
    products = [p for p in products if not p.get("graded")]
    filtered = any(x is not None for x in (condition, language, reverse, first_edition))
    if filtered:
        products = [
            p for p in products
            if _match_filters(
                p.get("properties_hash"),
                condition=condition, language=language,
                reverse=reverse, first_edition=first_edition,
            )
        ]
    prices = sorted(
        c for c in (_price_to_cents(p.get("price")) for p in products) if c is not None
    )
    if not prices:
        return None
    idx = min(position, len(prices)) - 1  # 4° → indice 3, clamp
    return {
        "cents": prices[idx],
        "position": idx + 1,
        "total": len(prices),
        "all_cents": prices[:10],
        "filtered": filtered,
    }


# ── Scrittura prodotti ─────────────────────────────────────────────

def create_product(
    blueprint_id: int,
    price_eur: float,
    quantity: int = 1,
    condition: str = "Near Mint",
    language: Optional[str] = None,
    reverse: bool = False,
    first_edition: bool = False,
    description: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
) -> Any:
    """Mette in vendita: POST /products. price in EURO (decimale, come da
    doc: 0.04). Le properties (condizione, lingua, reverse, prima edizione)
    sono costruite in base a cio' che il blueprint supporta. error_mode strict
    per fallire su dati incoerenti."""
    props = build_product_properties(
        blueprint_id,
        condition=condition, language=language,
        reverse=reverse, first_edition=first_edition,
    )
    if properties:
        props.update(properties)
    body = {
        "blueprint_id": blueprint_id,
        "price": round(float(price_eur), 2),
        "quantity": int(quantity),
        "error_mode": "strict",
        "properties": props,
    }
    if description and description.strip():
        body["description"] = description.strip()
    return _request("POST", "/products", json=body)


def update_product(product_id: int, **fields) -> Any:
    return _request("PUT", f"/products/{product_id}", json=fields)


def delete_product(product_id: int) -> Any:
    return _request("DELETE", f"/products/{product_id}")
