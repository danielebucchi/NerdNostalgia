"""
Rimuove gli hashtag dalle description di tutti gli articoli importati da
Vinted gia' presenti nel DB. Idempotente: rieseguibile senza danni.

Usi tipici (da host):
  docker exec -it nerdnostalgia-backend \\
    python /app/scripts/clean_vinted_hashtags.py

Opzioni:
  --dry-run   Mostra cosa farebbe ma non scrive
  --ids 1,2   Limita a specifici article_id
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from utils.session import SessionLocal  # noqa: E402
from models.db import Article  # noqa: E402
from utils.vinted_client import strip_hashtags  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("clean_vinted_hashtags")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Non scrive sul DB")
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
        query = db.query(Article).filter(
            Article.vinted_item_id.isnot(None),
            Article.description.isnot(None),
            Article.description != "",
        )
        if forced_ids:
            query = query.filter(Article.id.in_(forced_ids))

        targets = query.order_by(Article.id.asc()).all()
        LOGGER.info("Articoli candidati: %d", len(targets))

        cleaned_count = 0
        unchanged_count = 0
        emptied_count = 0

        for art in targets:
            new_descr = strip_hashtags(art.description)
            if new_descr == art.description:
                unchanged_count += 1
                continue

            if not new_descr:
                # La descrizione era SOLO hashtag → meglio lasciarla vuota
                # che mostrare una descrizione vuota di senso
                if args.dry_run:
                    LOGGER.info(
                        "[DRY] article %s: descrizione era solo hashtag, "
                        "verrebbe svuotata",
                        art.id,
                    )
                else:
                    art.description = None
                emptied_count += 1
                continue

            if args.dry_run:
                LOGGER.info(
                    "[DRY] article %s:\n  PRIMA: %s\n  DOPO:  %s",
                    art.id,
                    art.description[:120].replace("\n", " "),
                    new_descr[:120].replace("\n", " "),
                )
            else:
                art.description = new_descr
            cleaned_count += 1

        if not args.dry_run:
            db.commit()

        LOGGER.info(
            "Done: %d ripuliti, %d svuotati (solo hashtag), %d gia' ok",
            cleaned_count, emptied_count, unchanged_count,
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
