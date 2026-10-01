"""
Prenotazione degli articoli legata al ciclo di vita dell'ordine.

Regola: appena un compratore crea l'ordine il pezzo esce dal catalogo, cosi'
nessun altro puo' ordinarlo mentre si aspetta il pagamento. Poi:

  ordine PAGATO     → articolo VENDUTO (prenotazione sciolta)
  ordine ANNULLATO  → prenotazione sciolta, l'articolo torna in vendita
  ordine in attesa  → resta prenotato

Teniamo la prenotazione separata dallo stato: annullando, l'articolo torna
esattamente com'era (anche se era in bozza) senza doverci ricordare nulla.
"""
import logging
from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from models.db import Article, ArticleStatus, Order

LOGGER = logging.getLogger("reservation")


def _articles_of(db: Session, order: Order) -> List[Article]:
    ids = [it.article_id for it in order.items if it.article_id is not None]
    if not ids:
        return []
    return db.query(Article).filter(Article.id.in_(ids)).all()


def unavailable_article_ids(db: Session, article_ids: List[int]) -> List[int]:
    """Articoli gia' impegnati da un altro ordine in attesa. Serve a rifiutare
    il secondo compratore sullo stesso pezzo unico."""
    if not article_ids:
        return []
    rows = (
        db.query(Article.id)
        .filter(Article.id.in_(article_ids), Article.reserved_order_id.isnot(None))
        .all()
    )
    return [r[0] for r in rows]


def reserve_for_order(db: Session, order: Order) -> None:
    """Toglie dal catalogo i pezzi dell'ordine appena creato."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for article in _articles_of(db, order):
        article.reserved_order_id = order.id
        article.reserved_at = now
    db.commit()
    LOGGER.info("Articoli dell'ordine %s prenotati", order.id)


def release_order(db: Session, order: Order) -> None:
    """Scioglie la prenotazione: i pezzi tornano acquistabili. Tocca solo
    quelli ancora legati a QUESTO ordine, per non liberare per sbaglio un
    articolo nel frattempo riservato a un ordine piu' recente."""
    for article in _articles_of(db, order):
        if article.reserved_order_id == order.id:
            article.reserved_order_id = None
            article.reserved_at = None
    db.commit()
    LOGGER.info("Prenotazioni dell'ordine %s sciolte", order.id)


def mark_sold(db: Session, order: Order) -> None:
    """Pagamento incassato: i pezzi diventano VENDUTI e lasciano la
    prenotazione. Non tocchiamo gli articoli gia' venduti né quelli finiti nel
    frattempo su un altro ordine."""
    for article in _articles_of(db, order):
        if article.reserved_order_id in (order.id, None):
            article.status = ArticleStatus.SOLD
            article.reserved_order_id = None
            article.reserved_at = None
    db.commit()
    LOGGER.info("Articoli dell'ordine %s marcati VENDUTI", order.id)
