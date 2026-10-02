"""
API recensioni del venditore.

Si recensisce solo un ordine COMPLETATO, e lo si fa con (id + public_token)
dell'ordine: lo stesso token che serve a seguirne lo stato. Cosi' puo'
scrivere anche chi ha comprato da ospite, senza doversi registrare, e
soprattutto non puo' scrivere chi non ha comprato nulla.

Niente va online da solo: tutto nasce PENDING e lo pubblica l'admin.

NB: NIENTE `from __future__ import annotations` (vedi api/orders.py).
"""
import logging
import secrets
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from models.db import Order, OrderStatus, Review, ReviewStatus, User
from utils.limiter import limiter
from utils.session import get_db

LOGGER = logging.getLogger("reviews")

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


class ReviewCreate(BaseModel):
    order_id: int = Field(..., ge=1)
    token: str = Field(..., min_length=8, max_length=64)
    rating: int = Field(..., ge=1, le=5)
    body: Optional[str] = Field(None, max_length=2000)


class ReviewPublic(BaseModel):
    """Quello che si vede sul sito: niente id ordine, niente email."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    author_name: str
    rating: int
    body: Optional[str]
    reply: Optional[str]
    created_at: datetime


class ReviewAdmin(ReviewPublic):
    order_id: int
    status: ReviewStatus
    moderated_at: Optional[datetime]


class ReviewModerate(BaseModel):
    status: Optional[ReviewStatus] = None
    reply: Optional[str] = Field(None, max_length=2000)


def _reviewable_order(order_id: int, token: str, db: Session) -> Order:
    """L'ordine deve esistere, il token combaciare ed essere completato.

    Token sbagliato → 404 come un ordine inesistente: gli id non devono
    essere enumerabili per scoprire chi ha comprato cosa.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or not order.public_token:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    if not secrets.compare_digest(str(order.public_token), token):
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    if order.status != OrderStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Si può recensire solo dopo che l'ordine è stato completato.",
        )
    return order


@router.get("/can-review")
@limiter.limit("30/minute")
def can_review(
    request: Request,
    order_id: int = Query(..., ge=1),
    token: str = Query(..., min_length=8, max_length=64),
    db: Session = Depends(get_db),
):
    """Serve alla pagina di recensione per sapere cosa mostrare prima che
    l'utente scriva: il modulo, oppure "hai già recensito"."""
    order = _reviewable_order(order_id, token, db)
    esistente = db.query(Review).filter(Review.order_id == order.id).first()
    return {
        "order_id": order.id,
        "buyer_name": order.buyer_name,
        "already_reviewed": esistente is not None,
    }


@router.post("/", response_model=ReviewPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute;20/hour")
def create_review(
    payload: ReviewCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Scrive la recensione. Resta in attesa finché l'admin non la pubblica."""
    order = _reviewable_order(payload.order_id, payload.token, db)

    if db.query(Review).filter(Review.order_id == order.id).first():
        raise HTTPException(
            status_code=409,
            detail="Hai già lasciato una recensione per questo ordine. Grazie!",
        )

    review = Review(
        order_id=order.id,
        user_id=order.user_id,
        author_name=order.buyer_name,
        rating=payload.rating,
        body=(payload.body or "").strip() or None,
        status=ReviewStatus.PENDING,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    LOGGER.info("Nuova recensione %s★ per l'ordine %s", review.rating, order.id)
    return review


@router.get("/", response_model=List[ReviewPublic])
def list_public_reviews(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Recensioni pubblicate, dalla più recente."""
    return (
        db.query(Review)
        .filter(Review.status == ReviewStatus.APPROVED)
        .order_by(Review.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/summary")
def reviews_summary(db: Session = Depends(get_db)):
    """Media e conteggio, per il riquadro riassuntivo."""
    approvate = (
        db.query(Review).filter(Review.status == ReviewStatus.APPROVED).all()
    )
    if not approvate:
        return {"count": 0, "average": None}
    media = sum(r.rating for r in approvate) / len(approvate)
    return {"count": len(approvate), "average": round(media, 2)}


# ─────────────────── Admin ───────────────────
@router.get("/admin", response_model=List[ReviewAdmin])
def list_all_reviews(
    status_filter: Optional[ReviewStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    q = db.query(Review)
    if status_filter:
        q = q.filter(Review.status == status_filter)
    return q.order_by(Review.created_at.desc()).all()


@router.patch("/{review_id}", response_model=ReviewAdmin)
def moderate_review(
    review_id: int,
    payload: ReviewModerate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Pubblica, rifiuta o risponde a una recensione."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Recensione non trovata")

    if payload.status is not None and payload.status != review.status:
        review.status = payload.status
        review.moderated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if payload.reply is not None:
        review.reply = payload.reply.strip() or None

    db.commit()
    db.refresh(review)
    return review
