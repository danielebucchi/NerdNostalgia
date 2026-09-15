#!/usr/bin/env python3
"""
Sync Vinted "client-side": fetcha il profilo da QUI (es. Mac dell'admin,
IP residenziale) e pusha gli items a NerdNostalgia in produzione, dove
Cloudflare blocca lo headless browser.

Usage:
    # imposta env (consigliato in ~/.config/nerdnostalgia/sync.env)
    export NERDNOSTALGIA_API_URL="https://api.nerdnostalgia.store"
    export NERDNOSTALGIA_USERNAME="admin"
    export NERDNOSTALGIA_PASSWORD="..."
    export VINTED_USER_ID="95521831"

    # esegui
    python sync_from_local.py

Dopo l'import fa un secondo giro di "riconciliazione": il server risponde
con gli item_id che ha a catalogo ma che non sono comparsi nel fetch, questo
script verifica uno a uno se sono davvero spariti da Vinted (404 su
/items/{id} — va fatto da qui, non dal server, per lo stesso motivo del
fetch) e rimanda i confermati a POST /api/vinted/reconcile, che li archivia.
Si disattiva con RECONCILE=0.

Exit code:
    0  ok (sync completata, anche con 0 nuovi items)
    1  errore di rete/login
    2  errore Playwright/Vinted (CF challenge, profilo down, ecc.)
    3  errore lato server (POST /api/vinted/import → non 2xx)
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

# Ci si appoggia ai moduli del backend per il client Vinted: assume di
# girare dentro lo stesso repo (es. backend/scripts/sync_from_local.py).
HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
if SRC.is_dir():
    sys.path.insert(0, str(SRC))

try:
    import requests
    from utils.vinted_client import (
        VintedClientError,
        fetch_user_items,
        verify_items_missing,
    )
except ImportError as exc:
    sys.stderr.write(
        f"Import error: {exc}\n"
        "Suggerito: crea un venv dentro backend/ e installa requirements.txt\n"
        "  python3 -m venv backend/.venv-sync\n"
        "  backend/.venv-sync/bin/pip install -r backend/src/requirements.txt\n"
        "  backend/.venv-sync/bin/python -m playwright install chromium\n"
    )
    sys.exit(1)


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("sync_from_local")


def env(name: str, required: bool = True) -> str:
    val = os.getenv(name, "").strip()
    if required and not val:
        LOGGER.error("Env var mancante: %s", name)
        sys.exit(1)
    return val


def login(api_url: str, username: str, password: str, timeout: int = 30) -> str:
    LOGGER.info("Login su %s", api_url)
    r = requests.post(
        f"{api_url}/api/auth/login",
        data={"username": username, "password": password},
        timeout=timeout,
    )
    if r.status_code != 200:
        LOGGER.error("Login fallito: HTTP %s — %s", r.status_code, r.text[:200])
        sys.exit(1)
    token = r.json().get("access_token")
    if not token:
        LOGGER.error("Login OK ma access_token mancante in risposta")
        sys.exit(1)
    return token


def serialize_items(items) -> list[dict]:
    """VintedItem (dataclass) → dict pronto per JSON. Skippa `raw` per
    ridurre la dimensione del payload (può essere KB per item)."""
    out = []
    for it in items:
        out.append({
            "item_id": it.item_id,
            "title": it.title,
            "description": it.description,
            "price": it.price,
            "currency": it.currency,
            "url": it.url,
            "photos": it.photos or [],
            "catalog_id": it.catalog_id,
            "catalog_branch_title": it.catalog_branch_title,
            "status": it.status,
        })
    return out


def push(
    api_url: str,
    token: str,
    items: list[dict],
    seen_item_ids: list[int] | None = None,
) -> dict | None:
    """Pusha gli items al server. Timeout volutamente alto: l'import lato
    server scarica le foto da Vinted CDN per ogni item, e per 100+ items
    può durare 10-20 minuti. Se il client va in timeout comunque, il
    server è quasi sempre arrivato in fondo (la sync è idempotente: un
    re-run skippa gli items già importati). Ritorna None su timeout.
    """
    LOGGER.info("Push di %d items a %s/api/vinted/import (timeout 30m)", len(items), api_url)
    try:
        # (connect, read) — read alto perché l'import è sincrono server-side
        r = requests.post(
            f"{api_url}/api/vinted/import",
            json={
                "items": items,
                "triggered_by": "remote",
                "seen_item_ids": seen_item_ids or [],
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=(30, 1800),
        )
    except requests.exceptions.ReadTimeout:
        LOGGER.warning(
            "Read timeout dal server (>30m). Il backend molto probabilmente "
            "sta ancora processando o ha già finito. La sync è idempotente: "
            "il prossimo run skippa gli items già importati."
        )
        return None

    if r.status_code >= 300:
        LOGGER.error("Import fallito: HTTP %s — %s", r.status_code, r.text[:300])
        sys.exit(3)
    return r.json()


def reconcile(api_url: str, token: str, candidate_ids: list[int]) -> None:
    """Verifica i candidati e archivia quelli davvero spariti da Vinted.

    Best-effort: qualunque intoppo qui non deve far fallire la sync, che a
    quel punto e' gia' andata a buon fine. `verify_items_missing` e' gia'
    conservativo di suo — su errore di rete NON marca l'item come mancante.
    """
    LOGGER.info("Riconciliazione: verifico %d candidati su Vinted…", len(candidate_ids))
    try:
        missing = sorted(verify_items_missing(candidate_ids))
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Verifica candidati fallita, non archivio nulla: %s", exc)
        return

    alive = len(candidate_ids) - len(missing)
    LOGGER.info(
        "Riconciliazione: %d confermati spariti, %d ancora vivi su Vinted",
        len(missing), alive,
    )
    if not missing:
        return

    if os.getenv("DRY_RUN") == "1":
        LOGGER.info("DRY_RUN=1, non archivio: %s", missing)
        return

    try:
        r = requests.post(
            f"{api_url}/api/vinted/reconcile",
            json={"missing_item_ids": missing, "triggered_by": "reconcile"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=(30, 300),
        )
    except requests.RequestException as exc:
        LOGGER.warning("POST /reconcile fallita: %s", exc)
        return

    if r.status_code >= 300:
        LOGGER.warning("Reconcile HTTP %s — %s", r.status_code, r.text[:300])
        return

    log = r.json()
    LOGGER.info(
        "Reconcile: archiviati=%s rifiutati=%s error=%s",
        log.get("items_archived"),
        log.get("items_skipped"),
        log.get("error_message"),
    )


def main() -> int:
    api_url   = env("NERDNOSTALGIA_API_URL").rstrip("/")
    username  = env("NERDNOSTALGIA_USERNAME")
    password  = env("NERDNOSTALGIA_PASSWORD")
    vinted_id = int(env("VINTED_USER_ID"))

    token = login(api_url, username, password)

    LOGGER.info("Fetch items per Vinted user %s (Playwright locale)…", vinted_id)
    try:
        items = list(fetch_user_items(vinted_id))
    except VintedClientError as exc:
        LOGGER.error("Vinted client: %s", exc)
        return 2
    LOGGER.info("Fetchati %d items", len(items))

    payload = serialize_items(items)
    # Tutti gli ID visti sul profilo, filtro NerdNostalgia escluso: servono
    # al server per capire quali articoli a catalogo non sono piu' comparsi.
    seen_ids = [it.item_id for it in items]

    if os.getenv("DRY_RUN") == "1":
        print(json.dumps(payload, indent=2, ensure_ascii=False)[:4000])
        LOGGER.info("DRY_RUN=1, non pusho.")
        return 0

    log = push(api_url, token, payload, seen_item_ids=seen_ids)
    if log is None:
        # Timeout: il server molto probabilmente ha finito comunque (vedi
        # `GET /api/vinted/logs` per confermare). Exit 0 perché la sync
        # è idempotente e il prossimo run riconcilia eventuali residui.
        return 0
    LOGGER.info(
        "Server response: fetched=%s imported=%s updated=%s skipped=%s error=%s",
        log.get("items_fetched"),
        log.get("items_imported"),
        log.get("items_updated"),
        log.get("items_skipped"),
        log.get("error_message"),
    )

    if os.getenv("RECONCILE", "1") != "1":
        LOGGER.info("RECONCILE=0, salto la riconciliazione.")
        return 0

    reason = log.get("reconcile_skipped_reason")
    if reason:
        LOGGER.warning("Riconciliazione saltata dal server: %s", reason)
        return 0

    if "reconcile_candidates" not in log:
        # Server non ancora aggiornato: ignora `seen_item_ids` e non risponde
        # coi candidati. L'import e' andato a buon fine comunque.
        LOGGER.warning(
            "Il server non supporta la riconciliazione (nessun "
            "reconcile_candidates in risposta): serve il deploy del backend."
        )
        return 0

    candidates = log["reconcile_candidates"]
    if not candidates:
        LOGGER.info("Riconciliazione: nessun candidato, catalogo allineato.")
        return 0

    reconcile(api_url, token, candidates)
    return 0


if __name__ == "__main__":
    sys.exit(main())
