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
    from utils.vinted_client import VintedClientError, fetch_user_items
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


def push(api_url: str, token: str, items: list[dict], timeout: int = 120) -> dict:
    LOGGER.info("Push di %d items a %s/api/vinted/import", len(items), api_url)
    r = requests.post(
        f"{api_url}/api/vinted/import",
        json={"items": items, "triggered_by": "remote"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    if r.status_code >= 300:
        LOGGER.error("Import fallito: HTTP %s — %s", r.status_code, r.text[:300])
        sys.exit(3)
    return r.json()


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
    if os.getenv("DRY_RUN") == "1":
        print(json.dumps(payload, indent=2, ensure_ascii=False)[:4000])
        LOGGER.info("DRY_RUN=1, non pusho.")
        return 0

    log = push(api_url, token, payload)
    LOGGER.info(
        "Server response: fetched=%s imported=%s updated=%s skipped=%s error=%s",
        log.get("items_fetched"),
        log.get("items_imported"),
        log.get("items_updated"),
        log.get("items_skipped"),
        log.get("error_message"),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
