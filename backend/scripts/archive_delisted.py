#!/usr/bin/env python3
"""
Archiviazione una tantum degli articoli non piu' su Vinted.

Nasce per il caso "il guardaroba Vinted e' stato svuotato in modo
definitivo": la riconciliazione notturna non puo' farlo da sola, e non
deve — il suo guardrail si rifiuta (giustamente) di agire quando il fetch
torna pochi item o zero, che e' esattamente lo scenario qui.

Questo script fa la stessa cosa ma supervisionata: elenca gli articoli
PUBLISHED con un link Vinted, controlla UNO A UNO in che stato e'
l'annuncio su Vinted e agisce di conseguenza:

    404/410 (annuncio rimosso)  -> ARCHIVED, o DELETE con
                                   --missing-action delete
    pagina viva, marcata venduto -> SOLD
    ancora in vendita            -> non si tocca
    blocco/timeout/non chiaro    -> non si tocca

Di default non cancella niente: ARCHIVED e SOLD sono reversibili
dall'admin. Con --missing-action delete gli annunci rimossi vengono
eliminati davvero (immagini comprese, irreversibile) e in quel caso
--backup-dir e' obbligatorio.

Usage:
    set -a; source ~/.config/nerdnostalgia/sync.env; set +a

    # 1. Dry run (default): dice cosa farebbe, non tocca niente
    backend/.venv-sync/bin/python backend/scripts/archive_delisted.py

    # 2. Esecuzione vera
    backend/.venv-sync/bin/python backend/scripts/archive_delisted.py --apply

Opzioni:
    --apply         archivia davvero (senza, e' un dry run)
    --limit N       ferma la verifica ai primi N articoli
    --skip-verify   salta il controllo per item e archivia tutto quello
                    che e' PUBLISHED con link Vinted. SOLO per un
                    guardaroba confermato vuoto: salta la rete di
                    sicurezza e non distingue i venduti.

Exit code:
    0  ok    1  errore rete/login    2  errore Playwright/Vinted
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
if SRC.is_dir():
    sys.path.insert(0, str(SRC))

import requests  # noqa: E402
from utils.vinted_client import classify_items  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("archive_delisted")

ITEM_ID_RE = re.compile(r"/items/(\d+)")
PAGE_SIZE = 100


def env(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        LOGGER.error("Env var mancante: %s", name)
        sys.exit(1)
    return val


def login(api_url: str, username: str, password: str) -> str:
    r = requests.post(
        f"{api_url}/api/auth/login",
        data={"username": username, "password": password},
        timeout=30,
    )
    if r.status_code != 200:
        LOGGER.error("Login fallito: HTTP %s — %s", r.status_code, r.text[:200])
        sys.exit(1)
    token = r.json().get("access_token")
    if not token:
        LOGGER.error("Login OK ma access_token mancante")
        sys.exit(1)
    return token


def fetch_published(api_url: str, token: str) -> list[dict]:
    """Tutti gli articoli PUBLISHED che hanno un link Vinted.

    L'item_id si ricava da vinted_url perche' la ArticleResponse non
    espone vinted_item_id.
    """
    headers = {"Authorization": f"Bearer {token}"}
    out: list[dict] = []
    skip = 0
    while True:
        r = requests.get(
            f"{api_url}/api/articles/",
            params={"status": "PUBLISHED", "limit": PAGE_SIZE, "skip": skip},
            headers=headers,
            timeout=60,
        )
        if r.status_code != 200:
            LOGGER.error("GET articles HTTP %s — %s", r.status_code, r.text[:200])
            sys.exit(1)
        page = r.json()
        items = page.get("items") or []
        for a in items:
            m = ITEM_ID_RE.search(a.get("vinted_url") or "")
            if m:
                out.append({
                    "id": a["id"],
                    "item_id": int(m.group(1)),
                    "title": a.get("title") or "",
                    "synced_at": (a.get("vinted_synced_at") or "")[:10],
                })
        if len(items) < PAGE_SIZE:
            break
        skip += PAGE_SIZE
    return out


def set_status(api_url: str, token: str, article_id: int, status: str) -> bool:
    r = requests.patch(
        f"{api_url}/api/articles/{article_id}",
        json={"status": status},
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    if r.status_code >= 300:
        LOGGER.warning(
            "PATCH articolo %s fallita: HTTP %s — %s",
            article_id, r.status_code, r.text[:200],
        )
        return False
    return True


def delete_article(api_url: str, token: str, article_id: int) -> bool:
    r = requests.delete(
        f"{api_url}/api/articles/{article_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    if r.status_code not in (200, 204):
        LOGGER.warning(
            "DELETE articolo %s fallita: HTTP %s — %s",
            article_id, r.status_code, r.text[:200],
        )
        return False
    return True


def dump_backup(api_url: str, token: str, rows: list[dict], out_dir: str) -> Path:
    """Salva il record completo degli articoli che stanno per sparire."""
    headers = {"Authorization": f"Bearer {token}"}
    full = []
    for r in rows:
        try:
            resp = requests.get(
                f"{api_url}/api/articles/{r['id']}", headers=headers, timeout=30,
            )
            full.append(resp.json() if resp.status_code == 200 else {"id": r["id"], "errore": resp.status_code})
        except Exception as exc:  # noqa: BLE001
            full.append({"id": r["id"], "errore": repr(exc)})
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / "articoli-cancellati.json"
    path.write_text(json.dumps(full, indent=2, ensure_ascii=False, default=str))
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="archivia davvero")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--skip-verify", action="store_true")
    ap.add_argument(
        "--missing-action", choices=("archive", "delete"), default="archive",
        help="cosa fare degli annunci rimossi da Vinted (default: archive)",
    )
    ap.add_argument(
        "--backup-dir", default=None,
        help="dove salvare il dump degli articoli prima di toccarli "
             "(obbligatorio con --missing-action delete --apply)",
    )
    args = ap.parse_args()

    api_url = env("NERDNOSTALGIA_API_URL").rstrip("/")
    token = login(api_url, env("NERDNOSTALGIA_USERNAME"), env("NERDNOSTALGIA_PASSWORD"))

    rows = fetch_published(api_url, token)
    if args.limit:
        rows = rows[: args.limit]
    LOGGER.info("Articoli PUBLISHED con link Vinted: %d", len(rows))
    if not rows:
        return 0

    if args.skip_verify:
        LOGGER.warning(
            "--skip-verify: archivio tutto senza controllare i singoli annunci."
        )
        stato = {r["item_id"]: "missing" for r in rows}
    else:
        ids = [r["item_id"] for r in rows]
        LOGGER.info("Controllo %d annunci su Vinted (uno a uno)…", len(ids))
        try:
            stato = classify_items(ids)
            # Secondo passaggio sugli incerti: quasi sempre sono vittime
            # del rate-limit, non annunci realmente ambigui. Ripassarli da
            # soli, a freddo, ne recupera la gran parte.
            incerti = [i for i, v in stato.items() if v == "unknown"]
            if incerti and len(incerti) < len(ids):
                LOGGER.info(
                    "Ripasso %d item rimasti incerti, dopo una pausa…",
                    len(incerti),
                )
                time.sleep(60)
                stato.update(classify_items(incerti))
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("Controllo fallito, non tocco niente: %s", exc)
            return 2

    for r in rows:
        r["stato"] = stato.get(r["item_id"], "unknown")

    # missing -> ARCHIVED (annuncio rimosso), sold -> SOLD (venduto su
    # Vinted: lo stato giusto perche' l'articolo entri nello storico
    # vendite invece di sparire e basta). live/unknown non si toccano.
    piano = {
        "missing": "DELETE" if args.missing_action == "delete" else "ARCHIVED",
        "sold": "SOLD",
    }
    targets = [r for r in rows if r["stato"] in piano]

    conteggi = {}
    for r in rows:
        conteggi[r["stato"]] = conteggi.get(r["stato"], 0) + 1
    LOGGER.info("Esito controllo: %s", conteggi)
    intoccabili = [r for r in rows if r["stato"] in ("live", "unknown")]
    if intoccabili:
        LOGGER.info(
            "%d articoli restano PUBLISHED (ancora in vendita o non "
            "classificabili con certezza).", len(intoccabili),
        )

    if not targets:
        LOGGER.info("Niente da cambiare.")
        return 0

    print()
    print(f"{'ART':>5}  {'ITEM':>12}  {'ULT.SYNC':10}  {'NUOVO':8}  TITOLO")
    for t in sorted(targets, key=lambda r: r["stato"]):
        print(f"{t['id']:>5}  {t['item_id']:>12}  {t['synced_at']:10}  "
              f"{piano[t['stato']]:8}  {t['title'][:46]}")
    print()

    if not args.apply:
        riepilogo = {}
        for t in targets:
            azione = piano[t["stato"]]
            riepilogo[azione] = riepilogo.get(azione, 0) + 1
        LOGGER.info(
            "DRY RUN: toccherei %d articoli — %s. Rilancia con --apply.",
            len(targets),
            ", ".join(f"{n} {a}" for a, n in sorted(riepilogo.items())),
        )
        return 0

    da_cancellare = [t for t in targets if piano[t["stato"]] == "DELETE"]
    if da_cancellare:
        # La delete porta via anche la cartella immagini: senza un dump
        # locale non resterebbe traccia di cosa c'era.
        if not args.backup_dir:
            LOGGER.error(
                "--missing-action delete richiede --backup-dir: mi rifiuto "
                "di cancellare %d articoli senza salvarne una copia.",
                len(da_cancellare),
            )
            return 1
        path = dump_backup(api_url, token, da_cancellare, args.backup_dir)
        LOGGER.info("Backup di %d articoli in %s", len(da_cancellare), path)

    ok = fail = 0
    for t in targets:
        azione = piano[t["stato"]]
        done = (
            delete_article(api_url, token, t["id"]) if azione == "DELETE"
            else set_status(api_url, token, t["id"], azione)
        )
        if done:
            ok += 1
        else:
            fail += 1
    LOGGER.info(
        "Fatto: %d/%d articoli (%d cancellati, %d falliti).",
        ok, len(targets), sum(1 for t in da_cancellare) if not fail else len(da_cancellare), fail,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
