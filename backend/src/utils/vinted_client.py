"""
Client minimale per l'endpoint interno (non documentato) di Vinted.

Vinted NON espone un'API pubblica. Questo modulo parla con l'endpoint
gateway /api/v2/users/{id}/items che il loro frontend usa per il profilo.

Strategie anti-bot:
  * UA realistico Chrome
  * Sessione persistente con cookie (la prima GET sulla homepage Vinted
    setta i cookie anti-CSRF/cloudflare)
  * Random sleep tra le pagine
  * Retry exponenziale su 429/5xx

Failure model:
  * Solleva VintedClientError con il dettaglio HTTP
  * Il chiamante (sync service) cattura, logga su DB, non rompe la app
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Iterator, List, Optional

import requests

LOGGER = logging.getLogger("vinted_client")

BASE_HOST = "https://www.vinted.it"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 20
MAX_RETRIES = 3


class VintedClientError(Exception):
    """Errore parlando con Vinted (HTTP, parsing, blocco anti-bot)."""


@dataclass
class VintedItem:
    """Subset normalizzato di un annuncio dal profilo."""
    item_id: int
    title: str
    description: Optional[str]
    price: Optional[float]
    currency: str
    url: str
    photos: List[str]
    catalog_id: Optional[int]
    catalog_branch_title: Optional[str]
    status: Optional[str]
    raw: dict


def _new_session() -> requests.Session:
    """Crea una session con headers realistici e cookie Vinted preimpostati
    tramite una GET sulla homepage."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": BASE_HOST + "/",
        "Origin": BASE_HOST,
        "DNT": "1",
        "Connection": "keep-alive",
    })
    # Warmup: ottiene cookie anti-CSRF / sessione
    try:
        s.get(BASE_HOST + "/", timeout=DEFAULT_TIMEOUT)
    except requests.RequestException as exc:
        raise VintedClientError(f"Warmup fallito: {exc}") from exc
    return s


def _request_with_retry(
    session: requests.Session,
    url: str,
    *,
    params: Optional[dict] = None,
) -> dict:
    """GET con retry exponenziale su 429/5xx. Solleva VintedClientError."""
    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            if resp.status_code in (429, 500, 502, 503, 504):
                # Backoff progressivo + jitter
                sleep = (2 ** attempt) + random.uniform(0, 1)
                LOGGER.warning(
                    "Vinted %s on %s, retry in %.1fs (attempt %d)",
                    resp.status_code, url, sleep, attempt + 1,
                )
                time.sleep(sleep)
                continue
            if resp.status_code == 403:
                raise VintedClientError(
                    f"403 Forbidden: probabile blocco anti-bot. "
                    f"Body: {resp.text[:200]}"
                )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            last_exc = exc
            sleep = (2 ** attempt) + random.uniform(0, 1)
            LOGGER.warning("Vinted request error %s, retry in %.1fs", exc, sleep)
            time.sleep(sleep)
    raise VintedClientError(
        f"Esauriti i retry su {url}: {last_exc}"
    ) from last_exc


def _parse_item(item: dict) -> VintedItem:
    """Normalizza il JSON Vinted nel nostro VintedItem."""
    photos = []
    for photo in item.get("photos") or []:
        url = photo.get("full_size_url") or photo.get("url")
        if url:
            photos.append(url)

    # Catalog tree: Vinted usa "catalog_id" + "catalog_branch_title"
    # (es. "Elettronica · Videogiochi · Console")
    branch_title = item.get("catalog_branch_title") or item.get("catalog", {}).get("title")

    price_amount = None
    price = item.get("price")
    if isinstance(price, dict):
        price_amount = float(price.get("amount") or 0) or None
        currency = price.get("currency_code") or "EUR"
    else:
        try:
            price_amount = float(price) if price is not None else None
        except (TypeError, ValueError):
            price_amount = None
        currency = item.get("currency") or "EUR"

    return VintedItem(
        item_id=int(item["id"]),
        title=item.get("title", ""),
        description=item.get("description"),
        price=price_amount,
        currency=currency,
        url=item.get("url") or f"{BASE_HOST}/items/{item['id']}",
        photos=photos,
        catalog_id=item.get("catalog_id"),
        catalog_branch_title=branch_title,
        status=item.get("status"),
        raw=item,
    )


def fetch_user_items(
    vinted_user_id: int,
    *,
    per_page: int = 50,
    max_pages: int = 10,
    sleep_between_pages: float = 1.5,
) -> Iterator[VintedItem]:
    """Itera tutti gli annunci di un profilo Vinted.

    Solleva VintedClientError se la chiamata fallisce.
    """
    session = _new_session()
    url = f"{BASE_HOST}/api/v2/users/{vinted_user_id}/items"

    for page in range(1, max_pages + 1):
        params = {
            "per_page": per_page,
            "page": page,
            "order": "newest_first",
        }
        data = _request_with_retry(session, url, params=params)

        items = data.get("items") or []
        if not items:
            break

        for raw in items:
            try:
                yield _parse_item(raw)
            except (KeyError, ValueError) as exc:
                LOGGER.warning("Skip item (parse error): %s", exc)
                continue

        # Se la pagina è stata l'ultima, esci
        if len(items) < per_page:
            break

        time.sleep(sleep_between_pages + random.uniform(0, 0.5))


def download_photo(url: str, max_bytes: int = 10 * 1024 * 1024) -> bytes:
    """Scarica una foto Vinted. max_bytes protegge da file enormi."""
    session = _new_session()
    resp = session.get(url, timeout=DEFAULT_TIMEOUT, stream=True)
    resp.raise_for_status()
    chunks = bytearray()
    for chunk in resp.iter_content(chunk_size=64 * 1024):
        chunks.extend(chunk)
        if len(chunks) > max_bytes:
            raise VintedClientError(
                f"Foto troppo grande (>{max_bytes // 1024 // 1024}MB): {url}"
            )
    return bytes(chunks)
