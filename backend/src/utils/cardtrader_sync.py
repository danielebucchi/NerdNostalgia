"""
Sync articolo → prodotto CardTrader (logica condivisa fra l'endpoint
manuale e l'auto-push alla pubblicazione).

CardTrader accetta solo carte agganciate a un blueprint: l'auto-push
scatta SOLO per articoli di categoria "carte" gia' abbinati.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from models.db import Article
from utils import cardtrader_client as ct

LOGGER = logging.getLogger("cardtrader_sync")

# Slug top-level considerati "carte" (l'auto-push agisce solo su questi)
CARD_TOP_SLUGS = {"carte", "cards"}


def is_card_article(article: Article) -> bool:
    cat = article.category
    if cat is None:
        return False
    top_slug = cat.slug if cat.parent_id is None else (cat.parent.slug if cat.parent else cat.slug)
    return (top_slug or "").lower() in CARD_TOP_SLUGS


def _extract_product_id(resp: Any) -> Optional[int]:
    if isinstance(resp, dict):
        if isinstance(resp.get("resource"), dict) and "id" in resp["resource"]:
            return resp["resource"]["id"]
        if "id" in resp:
            return resp["id"]
    if isinstance(resp, list) and resp and isinstance(resp[0], dict):
        return resp[0].get("id")
    return None


def publish_article(
    db,
    article: Article,
    *,
    price_eur: Optional[float] = None,
    price_position: int = 4,
    quantity: Optional[int] = None,
    condition: str = "Near Mint",
) -> Dict[str, Any]:
    """Crea (o aggiorna) il prodotto CardTrader per l'articolo.
    Solleva ValueError (dati) o ct.CardTraderError (API). Il chiamante
    decide se propagare (endpoint) o inghiottire (auto-push)."""
    if not article.cardtrader_blueprint_id:
        raise ValueError("Articolo non abbinato a un blueprint CardTrader")

    meta = None
    if price_eur is None:
        sug = ct.suggested_price_cents(article.cardtrader_blueprint_id, price_position)
        if not sug:
            raise ValueError("Nessuna inserzione di riferimento per il prezzo")
        price_eur = round(sug["cents"] / 100, 2)
        meta = sug

    qty = quantity or article.quantity or 1

    if article.cardtrader_product_id:
        ct.update_product(article.cardtrader_product_id, price=price_eur, quantity=qty)
        product_id = article.cardtrader_product_id
        action = "updated"
    else:
        resp = ct.create_product(
            blueprint_id=article.cardtrader_blueprint_id,
            price_eur=price_eur,
            quantity=qty,
            condition=condition,
        )
        product_id = _extract_product_id(resp)
        action = "created"

    article.cardtrader_product_id = product_id
    article.cardtrader_synced_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(article)
    return {
        "action": action,
        "product_id": product_id,
        "price_eur": price_eur,
        "quantity": qty,
        "price_meta": meta,
    }


def unpublish_article(db, article: Article) -> bool:
    """Rimuove il prodotto da CardTrader. Best-effort sul 404 (gia' rimosso)."""
    if not article.cardtrader_product_id:
        return False
    try:
        ct.delete_product(article.cardtrader_product_id)
    except ct.CardTraderError as exc:
        if exc.status != 404:
            raise
    article.cardtrader_product_id = None
    db.commit()
    db.refresh(article)
    return True


def auto_publish_if_card(db, article: Article) -> Optional[int]:
    """Hook alla pubblicazione sul sito: se e' una carta abbinata, la
    pubblica anche su CardTrader col prezzo 4°. Best-effort: non solleva
    mai (la pubblicazione sul sito non deve fallire per CardTrader)."""
    try:
        if not ct.is_configured():
            return None
        if not is_card_article(article):
            return None
        if not article.cardtrader_blueprint_id:
            LOGGER.info(
                "Auto-push CardTrader saltato: articolo %s carta ma senza blueprint",
                article.id,
            )
            return None
        res = publish_article(db, article)
        LOGGER.info(
            "Auto-push CardTrader: articolo %s → prodotto %s a %.2f€",
            article.id, res["product_id"], res["price_eur"],
        )
        return res["product_id"]
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Auto-push CardTrader fallito per articolo %s: %s", article.id, exc)
        return None


def auto_unpublish_on_sold(db, article: Article) -> None:
    """Hook alla vendita: toglie la carta da CardTrader per non venderla
    due volte. Best-effort."""
    try:
        if article.cardtrader_product_id and ct.is_configured():
            unpublish_article(db, article)
            LOGGER.info("Auto-unpublish CardTrader su vendita: articolo %s", article.id)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Auto-unpublish CardTrader fallito per articolo %s: %s", article.id, exc)
