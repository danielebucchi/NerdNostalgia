"""
Client Vinted basato su Playwright + Chromium headless.

Strategia: apriamo la pagina profilo Vinted in un vero browser; il loro JS
fa le chiamate /api/v2/users/{id}/items con i token corretti (loro lo
sanno fare, noi no). Intercettiamo le response XHR e leggiamo i JSON.

Mainteinance:
  * Se Vinted cambia la struttura JSON degli items → aggiorna _parse_item
  * Se cambia l'URL pattern dell'endpoint → aggiorna ITEMS_URL_PATTERN
  * Se introducono captcha → ci accorgiamo dal timeout, log esplicito
"""
from __future__ import annotations

import logging
import random
import re
import time
from dataclasses import dataclass
from typing import Iterator, List, Optional

import requests
from playwright.sync_api import (
    Playwright,
    Response as PWResponse,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

LOGGER = logging.getLogger("vinted_client")

BASE_HOST = "https://www.vinted.it"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
NAV_TIMEOUT_MS = 30_000  # 30s per la navigazione iniziale
LOAD_MORE_WAIT_MS = 5_000

# Match dell'URL dell'endpoint XHR: cattura sia "/users/<id>/items" che
# eventuali variazioni future "/wardrobe/<id>/items" o "/catalog/items?user_id=..."
ITEMS_URL_PATTERN = re.compile(
    r"/api/v2/(?:users|wardrobe)/\d+/items|/api/v2/catalog/items"
)


class VintedClientError(Exception):
    """Errore parlando con Vinted (navigazione, intercept, parsing)."""


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


def _parse_item(item: dict) -> VintedItem:
    """Normalizza il JSON di un singolo item Vinted nel nostro dataclass."""
    photos: List[str] = []
    for photo in item.get("photos") or []:
        url = photo.get("full_size_url") or photo.get("url")
        if url:
            photos.append(url)

    branch_title = item.get("catalog_branch_title") or (
        item.get("catalog", {}) or {}
    ).get("title")

    price_amount = None
    price = item.get("price")
    if isinstance(price, dict):
        try:
            price_amount = float(price.get("amount") or 0) or None
        except (TypeError, ValueError):
            price_amount = None
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


def _fetch_description_for_item(page, item_id: int, stats: dict) -> Optional[str]:
    """Recupera la description di un singolo item dalla pagina/API Vinted.

    Tenta in ordine:
      1) /api/v2/items/{id} via fetch lato browser (cookie/session ereditati).
         Ritorna il body completo del seller: la sorgente piu' attendibile.
      2) <meta property="og:description"> della pagina pubblica /items/{id}.
         Spesso e' un template marketing ("Compra ... su Vinted, risparmia"),
         ma in mancanza d'altro e' meglio di niente.

    Aggiorna stats con quale sorgente ha funzionato (utile in log).
    Ritorna la descrizione strippata o None se entrambe falliscono.
    """
    api_url = f"{BASE_HOST}/api/v2/items/{item_id}"
    try:
        descr = page.evaluate(
            """async (url) => {
                try {
                    const r = await fetch(url, {
                        headers: { 'Accept': 'application/json' },
                        credentials: 'include',
                    });
                    if (!r.ok) return null;
                    const j = await r.json();
                    return j?.item?.description ?? null;
                } catch (e) { return null; }
            }""",
            api_url,
        )
        if descr and isinstance(descr, str) and len(descr.strip()) > 5:
            stats["api"] = stats.get("api", 0) + 1
            return descr.strip()
    except Exception as exc:  # noqa: BLE001
        LOGGER.debug("Item %s API fetch failed: %s", item_id, exc)

    # Fallback: navigazione DOM + og:description
    item_url = f"{BASE_HOST}/items/{item_id}"
    try:
        page.goto(item_url, wait_until="domcontentloaded", timeout=15_000)
        descr = page.evaluate(
            """() => {
                const meta = document.querySelector('meta[property="og:description"]');
                return meta ? meta.content : null;
            }"""
        )
        if descr and len(descr.strip()) > 5:
            stats["og"] = stats.get("og", 0) + 1
            return descr.strip()
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Item %s page fetch failed: %s", item_id, exc)

    stats["fail"] = stats.get("fail", 0) + 1
    return None


def fetch_item_descriptions(item_ids: List[int], *, headless: bool = True) -> dict[int, str]:
    """Backfill standalone delle descrizioni: data una lista di vinted_item_id,
    apre Chromium, eredita i cookie visitando l'homepage e per ognuno prova
    prima l'API e poi og:description. Ritorna {item_id: description}.

    Pensato per essere chiamato da script CLI quando un sync passato non ha
    popolato alcune descrizioni (rate-limit episodico, og:description vuoto, ecc).
    """
    if not item_ids:
        return {}

    out: dict[int, str] = {}
    stats = {"api": 0, "og": 0, "fail": 0}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        def _new_page():
            ctx = browser.new_context(
                user_agent=USER_AGENT,
                locale="it-IT",
                viewport={"width": 1366, "height": 900},
            )
            pg = ctx.new_page()
            try:
                pg.goto(BASE_HOST + "/", wait_until="domcontentloaded", timeout=20_000)
            except Exception:  # noqa: BLE001
                pass
            time.sleep(1.0)
            return pg

        page = _new_page()
        try:
            for idx, item_id in enumerate(item_ids):
                if idx > 0 and idx % 8 == 0:
                    # Restart browser per evitare rate-limit cumulativo
                    browser.close()
                    time.sleep(2.0)
                    browser = p.chromium.launch(
                        headless=headless,
                        args=[
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-blink-features=AutomationControlled",
                        ],
                    )
                    page = _new_page()

                descr = _fetch_description_for_item(page, int(item_id), stats)
                if descr:
                    out[int(item_id)] = descr
                time.sleep(1.2 + random.uniform(0, 0.7))
        finally:
            try:
                browser.close()
            except Exception:  # noqa: BLE001
                pass

    LOGGER.info(
        "Backfill descrizioni: %d/%d (api=%d og=%d fail=%d)",
        len(out), len(item_ids), stats["api"], stats["og"], stats["fail"],
    )
    return out


def fetch_user_items(
    vinted_user_id: int,
    *,
    max_items: int = 200,
    headless: bool = True,
    scroll_attempts: int = 20,
    enrich_with_details: bool = True,
) -> Iterator[VintedItem]:
    """Itera tutti gli annunci di un profilo Vinted usando Chromium headless.

    Se enrich_with_details=True (default) per ogni item fa una seconda
    chiamata a /api/v2/items/{id} riusando i cookie del browser, per
    ottenere la descrizione completa e il catalog_id (che il listing
    sintetico del profilo non include).

    Solleva VintedClientError se la navigazione fallisce, Vinted mostra
    captcha o non si intercetta nessuna response.
    """
    collected_raw: List[dict] = []
    seen_ids: set[int] = set()
    error: Optional[str] = None

    def on_response(response: PWResponse) -> None:
        if not ITEMS_URL_PATTERN.search(response.url):
            return
        if response.status != 200:
            return
        try:
            payload = response.json()
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Risposta intercettata non JSON: %s", exc)
            return
        new_items = payload.get("items") or []
        for raw in new_items:
            try:
                item_id = int(raw["id"])
            except (KeyError, ValueError, TypeError):
                continue
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            collected_raw.append(raw)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context = browser.new_context(
                user_agent=USER_AGENT,
                locale="it-IT",
                viewport={"width": 1366, "height": 900},
                extra_http_headers={
                    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
                },
            )
            page = context.new_page()
            page.on("response", on_response)

            profile_url = f"{BASE_HOST}/member/{vinted_user_id}"
            try:
                page.goto(profile_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            except PlaywrightTimeoutError as exc:
                raise VintedClientError(
                    f"Timeout navigazione su {profile_url}: {exc}"
                ) from exc

            try:
                page.wait_for_load_state("networkidle", timeout=LOAD_MORE_WAIT_MS)
            except PlaywrightTimeoutError:
                pass

            # Scroll progressivo per caricare piu items (infinite scroll).
            # Strategia: scroll-to-bottom in JS (piu' affidabile di mouse.wheel,
            # che con virtualizzazione DOM puo' non triggerare i loader), poi
            # un'attesa generosa per dare tempo a Vinted di rispondere. Dopo 4
            # round senza nuovi items si esce. Log per round per diagnosi.
            last_count = len(collected_raw)
            stagnant_rounds = 0
            for i in range(scroll_attempts):
                if len(collected_raw) >= max_items:
                    break
                try:
                    page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )
                except Exception:  # noqa: BLE001
                    pass
                # mouse.wheel come refresh extra: alcuni listener Vinted lo
                # ascoltano e non scattano solo con scrollTo programmatico
                try:
                    page.mouse.wheel(0, 2000)
                except Exception:  # noqa: BLE001
                    pass
                try:
                    page.wait_for_load_state("networkidle", timeout=LOAD_MORE_WAIT_MS)
                except PlaywrightTimeoutError:
                    pass
                # Sleep generoso: meglio aspettare 2s in piu' che mollare il
                # batch successivo che sta arrivando
                time.sleep(2.5 + random.uniform(0, 0.8))

                current = len(collected_raw)
                gained = current - last_count
                LOGGER.info(
                    "Scroll round %d/%d: collected=%d (+%d)",
                    i + 1, scroll_attempts, current, gained,
                )
                if gained == 0:
                    stagnant_rounds += 1
                    if stagnant_rounds >= 4:
                        LOGGER.info(
                            "Stop scrolling: 4 round consecutivi senza nuovi items"
                        )
                        break
                else:
                    stagnant_rounds = 0
                    last_count = current

            # Final pass: aspetta ancora un secondo e ri-scrolla, perche' a
            # volte l'ultimo batch arriva dopo che il loop principale e' uscito
            try:
                page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight)"
                )
                page.wait_for_load_state("networkidle", timeout=LOAD_MORE_WAIT_MS)
            except Exception:  # noqa: BLE001
                pass
            time.sleep(2.0)
            LOGGER.info(
                "Profilo %d: %d items intercettati totali",
                vinted_user_id, len(collected_raw),
            )

            # Arricchimento descrizioni. Sorgenti in ordine di affidabilita':
            #  1) Vinted API /api/v2/items/{id} (richiesta lato browser, eredita
            #     cookies/session: piu' robusta, ritorna la VERA description del
            #     seller — non il template marketing di og:description).
            #  2) Tag <meta property="og:description"> della pagina pubblica
            #     (fallback se l'API risponde 403/429/captcha).
            # Restart browser ogni 8 items per stare sotto rate-limit cumulativo.
            if enrich_with_details:
                ids = [raw["id"] for raw in collected_raw[:max_items] if raw.get("id")]
                LOGGER.info("Fetch detail per %d items", len(ids))

                details_map: dict = {}

                def _fresh_browser():
                    """Crea browser+page nuovi (chiude i precedenti se passati)."""
                    b = p.chromium.launch(
                        headless=headless,
                        args=[
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-blink-features=AutomationControlled",
                        ],
                    )
                    ctx = b.new_context(
                        user_agent=USER_AGENT,
                        locale="it-IT",
                        viewport={"width": 1366, "height": 900},
                    )
                    pg = ctx.new_page()
                    try:
                        pg.goto(BASE_HOST + "/", wait_until="domcontentloaded", timeout=20_000)
                    except Exception:  # noqa: BLE001
                        pass
                    time.sleep(1.0)
                    return b, pg

                # Chiudo il browser corrente (che era per il profilo) e ne
                # apro uno fresco dedicato al backfill.
                browser.close()
                browser, page = _fresh_browser()

                stats = {"api": 0, "og": 0, "fail": 0}

                for idx, item_id in enumerate(ids[:200]):
                    if idx > 0 and idx % 8 == 0:
                        browser.close()
                        time.sleep(2.0)
                        browser, page = _fresh_browser()

                    descr = _fetch_description_for_item(page, int(item_id), stats)
                    if descr:
                        details_map[item_id] = {"description": descr}
                    time.sleep(1.2 + random.uniform(0, 0.7))

                # Applica i details
                non_null_descr = 0
                for raw in collected_raw[:max_items]:
                    detail = details_map.get(raw.get("id"))
                    if detail and detail.get("description"):
                        raw["description"] = detail["description"]
                        non_null_descr += 1
                LOGGER.info(
                    "Descrizioni popolate: %d/%d (api=%d og=%d fail=%d)",
                    non_null_descr, len(ids),
                    stats["api"], stats["og"], stats["fail"],
                )

            browser.close()
    except VintedClientError:
        raise
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
        LOGGER.exception("Errore Playwright")
        raise VintedClientError(f"Playwright fallito: {exc}") from exc

    if not collected_raw and error is None:
        raise VintedClientError(
            "Nessuna risposta API intercettata. Vinted potrebbe mostrare "
            "captcha o aver cambiato la struttura della pagina."
        )

    LOGGER.info("Vinted: %d items intercettati dal profilo %d",
                len(collected_raw), vinted_user_id)

    for raw in collected_raw[:max_items]:
        try:
            yield _parse_item(raw)
        except (KeyError, ValueError, TypeError) as exc:
            LOGGER.warning("Skip item (parse error): %s", exc)
            continue


def verify_items_missing(item_ids: list[int]) -> set[int]:
    """Per ogni item_id, verifica navigando a /items/{id} se l'annuncio
    e' davvero scomparso su Vinted. Ritorna set degli ID che NON esistono
    piu'. Usato per evitare cancellazioni accidentali quando lo scroll
    del profilo non carica tutti gli items.

    Detection criteri:
      - Pagina restituisce 404 o 410
      - Redirect verso pagina di errore (URL contiene 'not-found' o '404')
      - Titolo pagina contiene "Pagina non trovata" / "Page not found"
    """
    if not item_ids:
        return set()

    missing: set[int] = set()
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="it-IT",
            viewport={"width": 1366, "height": 900},
        )
        page = context.new_page()
        try:
            page.goto(BASE_HOST + "/", wait_until="domcontentloaded", timeout=20_000)
            time.sleep(1.0)
        except Exception:  # noqa: BLE001
            pass

        for i, item_id in enumerate(item_ids):
            # Restart browser ogni 8 per stare sotto rate-limit
            if i > 0 and i % 8 == 0:
                browser.close()
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
                context = browser.new_context(
                    user_agent=USER_AGENT,
                    locale="it-IT",
                    viewport={"width": 1366, "height": 900},
                )
                page = context.new_page()
                try:
                    page.goto(BASE_HOST + "/", timeout=20_000)
                    time.sleep(1.0)
                except Exception:  # noqa: BLE001
                    pass

            url = f"{BASE_HOST}/items/{item_id}"
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=15_000)
                final_url = page.url
                status = resp.status if resp else None

                is_missing = False
                if status in (404, 410):
                    is_missing = True
                elif final_url and ("not-found" in final_url or "/404" in final_url):
                    is_missing = True
                else:
                    # Check titolo pagina per messaggi di errore
                    title = page.title() or ""
                    title_lower = title.lower()
                    if any(s in title_lower for s in (
                        "pagina non trovata",
                        "page not found",
                        "404",
                        "non disponibile",
                    )):
                        is_missing = True

                if is_missing:
                    missing.add(item_id)
                    LOGGER.info("Item %d confermato MISSING su Vinted", item_id)
                time.sleep(0.8 + random.uniform(0, 0.5))
            except Exception as exc:  # noqa: BLE001
                # In caso di errore NON marchiamo missing (safety)
                LOGGER.warning("verify_items_missing #%d fail: %s", item_id, exc)
                continue

        browser.close()

    return missing


def download_photo(url: str, max_bytes: int = 10 * 1024 * 1024) -> bytes:
    """Scarica una foto Vinted via requests semplice. Le foto sono su CDN
    pubblico, niente auth necessaria."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "image/avif,image/webp,*/*",
        "Referer": BASE_HOST + "/",
    }
    resp = requests.get(url, headers=headers, timeout=20, stream=True)
    resp.raise_for_status()
    chunks = bytearray()
    for chunk in resp.iter_content(chunk_size=64 * 1024):
        chunks.extend(chunk)
        if len(chunks) > max_bytes:
            raise VintedClientError(
                f"Foto troppo grande (>{max_bytes // 1024 // 1024}MB): {url}"
            )
    return bytes(chunks)
