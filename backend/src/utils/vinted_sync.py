"""
Sync service Vinted → NerdNostalgia.

Pipeline:
  1) Legge vinted_settings (user_id, enabled)
  2) Fetcha tutti gli items del profilo (utils.vinted_client)
  3) Filtra solo gli items il cui catalog_id e' presente e abilitato
     in vinted_category_mappings (oppure il cui branch_title contiene
     parole-chiave da fallback)
  4) Per ogni item:
        - se vinted_item_id già esistente → aggiorna prezzo/titolo
        - altrimenti crea Article DRAFT mappato alla nostra categoria
  5) Scarica le foto via vinted_client + le converte in WebP locali
  6) Scrive vinted_sync_logs con counters
"""
from __future__ import annotations

import datetime as _dt
import io
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from models.db import (
    Article,
    ArticleCondition,
    ArticleStatus,
    User,
    VintedCategoryMapping,
    VintedSettings,
    VintedStatus,
    VintedSyncLog,
)
from utils.storage import (
    ARTICLES_UPLOADS_DIR,
    LARGE_MAX_WIDTH,
    THUMB_MAX_WIDTH,
    WEBP_QUALITY,
    public_url,
)
from utils.vinted_client import (
    VintedClientError,
    VintedItem,
    download_photo,
    fetch_user_items,
)

LOGGER = logging.getLogger("vinted_sync")

# Fallback keywords nel branch_title se il catalog_id non e' mappato.
# Esempio: nuovo catalog_id sub-categoria che ancora non conosciamo, ma
# il branch_title contiene "Elettronica" → e' un articolo NN.
FALLBACK_BRANCH_KEYWORDS = (
    "elettronica",
    "videogioch",  # videogioco/videogiochi
    "console",
    "collezionism",
    "carte",
    "pokemon",
    "magic",
    "yu-gi-oh",
    "funko",
    "action figure",
    "modellini",
)


def _branch_matches_fallback(branch_title: Optional[str]) -> bool:
    if not branch_title:
        return False
    lowered = branch_title.lower()
    return any(kw in lowered for kw in FALLBACK_BRANCH_KEYWORDS)


def _load_mapping(db: Session) -> dict[int, Optional[int]]:
    """Ritorna {vinted_catalog_id: nn_category_id} per i mapping enabled."""
    rows = (
        db.query(VintedCategoryMapping)
        .filter(VintedCategoryMapping.enabled.is_(True))
        .all()
    )
    return {r.vinted_catalog_id: r.category_id for r in rows}


def _admin_user_id(db: Session) -> int:
    """Trova l'id dell'admin (owner di default per gli articoli importati)."""
    user = db.query(User).order_by(User.id.asc()).first()
    if not user:
        raise RuntimeError("Nessun utente in DB, impossibile assegnare gli articoli importati")
    return user.id


def _save_photo(photo_bytes: bytes, article_id: int) -> Optional[str]:
    """Salva una foto Vinted come WebP locale (+ thumb). Ritorna l'URL pubblico."""
    try:
        with Image.open(io.BytesIO(photo_bytes)) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode in ("P", "RGBA"):
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")

            uid = uuid.uuid4().hex
            dest_dir = ARTICLES_UPLOADS_DIR / str(article_id)
            dest_dir.mkdir(parents=True, exist_ok=True)
            large_path = dest_dir / f"{uid}.webp"
            thumb_path = dest_dir / f"{uid}.thumb.webp"

            def resize(image: Image.Image, max_width: int) -> bytes:
                if image.width > max_width:
                    ratio = max_width / float(image.width)
                    image = image.resize(
                        (max_width, int(image.height * ratio)),
                        Image.Resampling.LANCZOS,
                    )
                out = io.BytesIO()
                image.save(out, format="WEBP", quality=WEBP_QUALITY, method=6)
                return out.getvalue()

            large_path.write_bytes(resize(img.copy(), LARGE_MAX_WIDTH))
            thumb_path.write_bytes(resize(img.copy(), THUMB_MAX_WIDTH))

            relative = f"articles/{article_id}/{large_path.name}"
            return public_url(relative)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Save photo failed: %s", exc)
        return None


def _item_passes_filter(
    item: VintedItem,
    mapping: dict[int, Optional[int]],
) -> tuple[bool, Optional[int]]:
    """Decide se l'item passa il filtro. Ritorna (allowed, nn_category_id)."""
    # 1) Match diretto su catalog_id
    if item.catalog_id is not None and item.catalog_id in mapping:
        return True, mapping[item.catalog_id]

    # 2) Fallback: branch_title contiene keyword di elettronica/collezionismo
    if _branch_matches_fallback(item.catalog_branch_title):
        # Categoria non determinabile → lasciamo NULL (admin la setta a mano)
        return True, None

    return False, None


def _apply_item_to_article(
    db: Session,
    item: VintedItem,
    target_category_id: Optional[int],
    user_id: int,
) -> tuple[Article, str]:
    """Ritorna (article, op) dove op = 'created' | 'updated' | 'skipped'."""
    existing = (
        db.query(Article)
        .filter(Article.vinted_item_id == item.item_id)
        .first()
    )

    now = datetime.now(_dt.UTC)
    price = Decimal(str(item.price)) if item.price else Decimal("0")

    if existing is not None:
        # Update soft: solo prezzo + sync time, NON sovrascrivo titolo/descr/foto
        # (l'admin potrebbe averli editati). Se l'admin ha gia' pubblicato e Vinted
        # mostra venduto/non listato → aggiorno vinted_status.
        changed = False
        if existing.vinted_price != price:
            existing.vinted_price = price
            changed = True
        if existing.vinted_url != item.url:
            existing.vinted_url = item.url
            changed = True
        new_status = (
            VintedStatus.SOLD if (item.status or "").lower() == "sold"
            else VintedStatus.LISTED
        )
        if existing.vinted_status != new_status:
            existing.vinted_status = new_status
            changed = True
        existing.vinted_synced_at = now
        if changed:
            db.commit()
            db.refresh(existing)
            return existing, "updated"
        return existing, "skipped"

    # Nuovo articolo: bozza
    article = Article(
        user_id=user_id,
        title=item.title or f"Vinted #{item.item_id}",
        description=item.description,
        price=price,
        currency=item.currency or "EUR",
        condition=ArticleCondition.USED,
        status=ArticleStatus.DRAFT,
        quantity=1,
        category_id=target_category_id,
        images=[],
        vinted_item_id=item.item_id,
        vinted_url=item.url,
        vinted_price=price,
        vinted_status=(
            VintedStatus.SOLD if (item.status or "").lower() == "sold"
            else VintedStatus.LISTED
        ),
        vinted_synced_at=now,
        purchase_platform="Vinted",
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    # Scarica le foto (best-effort, limita a 8 per articolo)
    saved_urls: List[str] = []
    for url in (item.photos or [])[:8]:
        try:
            data = download_photo(url)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Download photo failed for %s: %s", url, exc)
            continue
        saved = _save_photo(data, article.id)
        if saved:
            saved_urls.append(saved)

    if saved_urls:
        article.images = saved_urls
        db.commit()
        db.refresh(article)

    return article, "created"


def run_sync(db: Session, triggered_by: str = "cron") -> VintedSyncLog:
    """Esegue la sync e ritorna il log scritto su DB."""
    settings = db.query(VintedSettings).order_by(VintedSettings.id.asc()).first()
    log = VintedSyncLog(
        started_at=datetime.now(_dt.UTC),
        triggered_by=triggered_by,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    if settings is None or not settings.enabled:
        log.finished_at = datetime.now(_dt.UTC)
        log.error_message = "Sync Vinted disabilitata o non configurata"
        db.commit()
        return log

    mapping = _load_mapping(db)
    user_id = _admin_user_id(db)

    fetched = 0
    imported = 0
    updated = 0
    skipped = 0

    try:
        for item in fetch_user_items(settings.vinted_user_id):
            fetched += 1
            allowed, target_cat = _item_passes_filter(item, mapping)
            if not allowed:
                skipped += 1
                continue
            try:
                _, op = _apply_item_to_article(db, item, target_cat, user_id)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Errore importando item %s", item.item_id)
                skipped += 1
                continue
            if op == "created":
                imported += 1
            elif op == "updated":
                updated += 1
            else:
                skipped += 1

        settings.last_run_at = datetime.now(_dt.UTC)
        db.commit()
    except VintedClientError as exc:
        log.error_message = f"Client Vinted: {exc}"
        LOGGER.error("Vinted sync fallita: %s", exc)
    except Exception as exc:  # noqa: BLE001
        log.error_message = f"Errore inatteso: {exc}"
        LOGGER.exception("Vinted sync inattesa")
    finally:
        log.finished_at = datetime.now(_dt.UTC)
        log.items_fetched = fetched
        log.items_imported = imported
        log.items_updated = updated
        log.items_skipped = skipped
        db.commit()
        db.refresh(log)

    return log
