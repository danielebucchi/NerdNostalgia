"""
Backfill delle descrizioni mancanti su articoli importati da Vinted.

Trova tutti gli Article con vinted_item_id valorizzato e description vuota,
chiama Vinted per recuperare la descrizione vera (API /api/v2/items/{id}
prima, og:description come fallback) e popola il DB.

Usi tipici (da host):
  docker exec -it nerdnostalgia-backend \\
    python /app/scripts/backfill_vinted_descriptions.py

Opzioni:
  --dry-run   Mostra cosa farebbe ma non scrive sul DB
  --limit N   Processa al massimo N articoli (default: tutti)
  --ids 1,2,3 Forza solo questi article_id (utile per fix puntuali)
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Permetti import "flat" come in prod
SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import or_

from utils.session import SessionLocal  # noqa: E402
from models.db import Article  # noqa: E402
from utils.vinted_client import fetch_item_descriptions  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("backfill_vinted_descriptions")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Non scrive sul DB")
    parser.add_argument("--limit", type=int, default=None, help="Max articoli da processare")
    parser.add_argument(
        "--ids",
        type=str,
        default=None,
        help="Lista CSV di article_id da forzare (es: 12,15,40)",
    )
    args = parser.parse_args()

    forced_ids: list[int] | None = None
    if args.ids:
        try:
            forced_ids = [int(x) for x in args.ids.split(",") if x.strip()]
        except ValueError:
            LOGGER.error("--ids accetta solo interi separati da virgola")
            return 2

    db = SessionLocal()
    try:
        query = db.query(Article).filter(Article.vinted_item_id.isnot(None))
        if forced_ids:
            query = query.filter(Article.id.in_(forced_ids))
        else:
            # Solo articoli con description mancante o vuota
            query = query.filter(
                or_(Article.description.is_(None), Article.description == "")
            )

        query = query.order_by(Article.id.asc())
        if args.limit:
            query = query.limit(args.limit)

        targets = query.all()
        if not targets:
            LOGGER.info("Nessun articolo da aggiornare. Tutto a posto.")
            return 0

        LOGGER.info(
            "Articoli da processare: %d (dry_run=%s)",
            len(targets), args.dry_run,
        )

        item_ids = [int(a.vinted_item_id) for a in targets]
        id_to_article = {int(a.vinted_item_id): a for a in targets}

        descriptions = fetch_item_descriptions(item_ids)

        updated = 0
        skipped = 0
        for vinted_id, descr in descriptions.items():
            article = id_to_article.get(vinted_id)
            if not article:
                continue
            if not args.dry_run:
                article.description = descr
                updated += 1
            else:
                LOGGER.info(
                    "[DRY] article %s (vinted %s) → %s...",
                    article.id, vinted_id, descr[:80].replace("\n", " "),
                )
                updated += 1

        skipped = len(targets) - updated
        if not args.dry_run:
            db.commit()

        LOGGER.info(
            "Done: %d aggiornati, %d senza descrizione recuperabile",
            updated, skipped,
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
