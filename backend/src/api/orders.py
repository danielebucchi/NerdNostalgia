"""
API ordini di acquisto.

Pubblici:
  POST /api/orders          → crea un ordine PENDING + manda email all'admin

Admin:
  GET   /api/orders         → lista ordini con filtri
  GET   /api/orders/{id}    → dettaglio ordine
  PATCH /api/orders/{id}    → cambia status / admin_notes
  DELETE /api/orders/{id}   → cancella

Il pagamento PayPal e' out-of-band: l'admin conferma manualmente quando
riceve il bonifico (PATCH status=PAID).

Rate-limit: 3/min, 20/h per IP. Honeypot anti-bot via campo 'website'.

NB: NIENTE `from __future__ import annotations` qui — FastAPI usa
inspect.signature per capire quali parametri sono body / query / path,
e con annotation stringificate (PEP 563) trasforma erroneamente
`payload: OrderCreate` in un query parameter ForwardRef, mandando in
errore 422 ogni POST.
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from models.db import Article, ArticleStatus, Order, OrderItem, OrderStatus, User
from utils.email import send_order_notification
from utils.limiter import limiter
from utils.session import get_db

LOGGER = logging.getLogger("orders")

router = APIRouter(prefix="/api/orders", tags=["orders"])


# ─────────────────── Schemas Pydantic ───────────────────
class OrderItemIn(BaseModel):
    article_id: int = Field(..., ge=1)
    quantity: int = Field(1, ge=1, le=10)


class OrderCreate(BaseModel):
    # Buyer
    buyer_name: str = Field(..., min_length=2, max_length=255)
    buyer_email: EmailStr
    buyer_phone: Optional[str] = Field(None, max_length=50)
    # Indirizzo
    ship_street: str = Field(..., min_length=3, max_length=255)
    ship_city: str = Field(..., min_length=2, max_length=120)
    ship_postal_code: str = Field(..., min_length=3, max_length=20)
    ship_province: Optional[str] = Field(None, max_length=120)
    ship_country: str = Field("Italia", min_length=2, max_length=80)
    # Carrello
    items: List[OrderItemIn] = Field(..., min_length=1, max_length=20)
    notes: Optional[str] = Field(None, max_length=2000)
    # Honeypot anti-bot: deve restare vuoto
    website: Optional[str] = Field(None, max_length=200)


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    article_id: Optional[int]
    title_snapshot: str
    price_snapshot: Decimal
    quantity: int


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    buyer_name: str
    buyer_email: str
    buyer_phone: Optional[str]
    ship_street: str
    ship_city: str
    ship_postal_code: str
    ship_province: Optional[str]
    ship_country: str
    subtotal: Decimal
    shipping_total: Decimal
    grand_total: Decimal
    currency: str
    notes: Optional[str]
    status: OrderStatus
    paid_at: Optional[datetime]
    shipped_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    admin_notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse]


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    admin_notes: Optional[str] = None


# ─────────────────── Logica shipping aggregata ───────────────────
# Regola: per ordini multi-articolo, prendiamo il MAX delle shipping_price
# (chi paga per spedire una console copre anche le carte buttate nel pacco).
# Per articoli senza shipping_price → default 5€.
DEFAULT_SHIPPING = Decimal("5.00")


def _calc_shipping(articles: list[Article]) -> Decimal:
    """Spedizione aggregata. Politica: max delle shipping_price dei pezzi
    nel pacco. Senza shipping_price → 5€ default."""
    ships = [a.shipping_price or DEFAULT_SHIPPING for a in articles]
    return max(ships) if ships else DEFAULT_SHIPPING


# ─────────────────── Public endpoint: crea ordine ───────────────────
@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("3/minute;20/hour")
def create_order(
    payload: OrderCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Crea un ordine PENDING e manda email all'admin.

    NB: il pagamento PayPal e' un secondo step out-of-band. Questo endpoint
    NON aspetta il pagamento, registra solo l'intent del compratore.
    """
    # Honeypot: se il bot riempie 'website', simuliamo successo senza salvare
    if payload.website:
        LOGGER.info("Order honeypot trigger from IP %s", request.client.host if request.client else "?")
        # Ritorna oggetto "fake" che non viene davvero salvato
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="ok")

    # Risolvi articoli + validali (PUBLISHED, esistono)
    article_ids = [it.article_id for it in payload.items]
    articles = db.query(Article).filter(Article.id.in_(article_ids)).all()
    found_ids = {a.id for a in articles}
    missing = [aid for aid in article_ids if aid not in found_ids]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Articoli non trovati: {missing}",
        )

    not_buyable = [
        a.id for a in articles
        if a.status != ArticleStatus.PUBLISHED
    ]
    if not_buyable:
        raise HTTPException(
            status_code=400,
            detail=f"Articoli non disponibili (non PUBLISHED): {not_buyable}",
        )

    # Lookup articoli per item, calcoli (snapshot prezzi)
    art_by_id = {a.id: a for a in articles}
    subtotal = Decimal("0")
    items_to_insert: list[OrderItem] = []
    for it in payload.items:
        a = art_by_id[it.article_id]
        line_total = (a.price or Decimal("0")) * it.quantity
        subtotal += line_total
        items_to_insert.append(OrderItem(
            article_id=a.id,
            title_snapshot=a.title,
            price_snapshot=a.price or Decimal("0"),
            quantity=it.quantity,
        ))

    shipping_total = _calc_shipping(articles)
    grand_total = subtotal + shipping_total

    # IP per audit/rate-limit info
    ip = request.client.host if request.client else None

    order = Order(
        buyer_name=payload.buyer_name.strip(),
        buyer_email=str(payload.buyer_email),
        buyer_phone=(payload.buyer_phone or "").strip() or None,
        ship_street=payload.ship_street.strip(),
        ship_city=payload.ship_city.strip(),
        ship_postal_code=payload.ship_postal_code.strip(),
        ship_province=(payload.ship_province or "").strip() or None,
        ship_country=payload.ship_country.strip(),
        subtotal=subtotal,
        shipping_total=shipping_total,
        grand_total=grand_total,
        currency="EUR",
        notes=(payload.notes or "").strip() or None,
        status=OrderStatus.PENDING,
        ip_address=ip,
        items=items_to_insert,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # Email all'admin (best-effort, log se fallisce ma ordine resta valido)
    try:
        send_order_notification(order)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Email order notification failed: %s", exc)

    return order


# ─────────────────── Admin endpoints ───────────────────
@router.get("/", response_model=List[OrderResponse])
def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: Optional[OrderStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    q = db.query(Order)
    if status_filter:
        q = q.filter(Order.status == status_filter)
    q = q.order_by(Order.created_at.desc()).offset(skip).limit(limit)
    return q.all()


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    return order


@router.patch("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: int,
    payload: OrderUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")

    if payload.status is not None and payload.status != order.status:
        order.status = payload.status
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if payload.status == OrderStatus.PAID and not order.paid_at:
            order.paid_at = now
        elif payload.status == OrderStatus.SHIPPED and not order.shipped_at:
            order.shipped_at = now
        elif payload.status == OrderStatus.CANCELLED and not order.cancelled_at:
            order.cancelled_at = now

    if payload.admin_notes is not None:
        order.admin_notes = payload.admin_notes.strip() or None

    db.commit()
    db.refresh(order)
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    db.delete(order)
    db.commit()
    return None
