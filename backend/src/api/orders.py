"""
API ordini di acquisto.

Pubblici:
  POST /api/orders                 → crea un ordine PENDING + email all'admin
                                     (destinazione: un locker InPost)
  GET  /api/orders/{id}/status     → stato dell'ordine, serve (id + token)

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
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from helpers.shipping import (
    base_shipping,
    calc_shipping,
    insurance_fee,
    resolve_insured,
)
from helpers.reservation import (
    mark_sold,
    release_order,
    reserve_for_order,
    unavailable_article_ids,
)
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
    # Locker InPost scelto sulla mappa. Obbligatorio SOLO quando la mappa e'
    # configurata: senza token InPost il sito ripiega sulla consegna a
    # domicilio, altrimenti nessuno potrebbe comprare (vedi il controllo in
    # create_order).
    inpost_point_id: Optional[str] = Field(None, min_length=2, max_length=64)
    inpost_point_name: Optional[str] = Field(None, max_length=255)
    # Destinazione: l'indirizzo del locker se si ritira al punto, quello di
    # casa del compratore se si spedisce a domicilio.
    ship_street: str = Field(..., min_length=3, max_length=255)
    ship_city: str = Field(..., min_length=2, max_length=120)
    ship_postal_code: str = Field(..., min_length=3, max_length=20)
    ship_province: Optional[str] = Field(None, max_length=120)
    ship_country: str = Field("Italia", min_length=2, max_length=80)
    # Carrello
    items: List[OrderItemIn] = Field(..., min_length=1, max_length=20)
    notes: Optional[str] = Field(None, max_length=2000)
    # Assicurazione spedizione. None = lascia decidere al default della
    # fascia (attiva dai 50 € in su); True/False = scelta esplicita del
    # compratore, che puo' assicurare un ordine piccolo o rinunciare su uno
    # grande.
    insured: Optional[bool] = None
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
    # Locker di ritiro scelto dal compratore
    inpost_point_id: Optional[str] = None
    inpost_point_name: Optional[str] = None
    # Assicurazione: scelta e costo (gia' compresi in shipping_total)
    insured: bool = False
    insurance_fee: Decimal = Decimal("0")
    # Solo storico: l'offerta di consegna a mano non esiste piu' sul sito.
    hand_exchange: bool = False
    # Restituito alla creazione: il frontend lo conserva per interrogare
    # /status e capire quando il carrello puo' essere svuotato.
    public_token: Optional[str] = None
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


def _free_shipping_all(db: Session) -> bool:
    """Promozione "spedizione gratuita su tutto" dalle settings runtime.
    In caso di problemi si ripiega sul comportamento normale: meglio far
    pagare la spedizione che regalarla per un errore di lettura."""
    try:
        from helpers.setting import SettingHelper
        raw = SettingHelper(db=db).get_value("free_shipping_all")
        return (raw or "").strip().lower() == "true"
    except Exception:  # noqa: BLE001
        return False


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

    # Pezzi unici: se qualcun altro ha gia' un ordine aperto su questo
    # articolo, il secondo compratore si ferma qui. E' il controllo che
    # conta davvero — l'interfaccia puo' sempre essere aggirata.
    # Consegna al locker: obbligatoria solo se la mappa e' attiva. Cosi' il
    # giorno in cui arriva il token InPost il sito passa al locker da solo, e
    # finche' non arriva continua a vendere con la consegna a domicilio.
    from api.inpost import is_configured as inpost_configured
    if inpost_configured() and not (payload.inpost_point_id or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Scegli sulla mappa il locker InPost dove ritirare il pacco.",
        )

    taken = unavailable_article_ids(db, article_ids)
    if taken:
        raise HTTPException(
            status_code=409,
            detail=(
                "Qualcuno ha appena ordinato questo articolo e lo stiamo "
                "tenendo da parte in attesa del suo pagamento. Riprova fra "
                "qualche ora: se l'ordine non va a buon fine torna disponibile."
            ),
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

    # Spedizione a scaglioni sul subtotale + assicurazione facoltativa
    # (vedi helpers/shipping.py). La calcola il server, mai il browser:
    # dal client arriva solo la scelta si/no sull'assicurazione.
    #
    # L'interruttore "spedizione gratuita su tutto" di /admin/impostazioni
    # azzera la riga intera: e' una promozione, non uno sconto sul singolo
    # ordine, quindi la decisione sta nelle settings e non nel payload.
    free_all = _free_shipping_all(db)
    insured = resolve_insured(subtotal, payload.insured)
    insurance = Decimal("0.00") if free_all else insurance_fee(subtotal, insured)
    shipping_total = Decimal("0.00") if free_all else base_shipping(subtotal) + insurance
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
        inpost_point_id=(payload.inpost_point_id or "").strip() or None,
        insured=insured,
        insurance_fee=insurance,
        inpost_point_name=(payload.inpost_point_name or "").strip() or None,
        public_token=secrets.token_urlsafe(24),
        status=OrderStatus.PENDING,
        ip_address=ip,
        items=items_to_insert,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # Toglie i pezzi dal catalogo: nessun altro puo' ordinarli finche'
    # questo ordine non viene confermato o annullato.
    reserve_for_order(db, order)

    # Email all'admin (best-effort, log se fallisce ma ordine resta valido)
    try:
        send_order_notification(order)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Email order notification failed: %s", exc)

    return order


# ─────────────────── Public endpoint: stato ordine ───────────────────
# Il compratore non e' autenticato: l'unica prova che l'ordine e' suo e' il
# token opaco ricevuto alla creazione. Senza token (o con token sbagliato)
# rispondiamo 404 come per un ordine inesistente, cosi' gli id non sono
# enumerabili. Esponiamo solo lo stato: niente indirizzo, niente importi.
PAID_STATUSES = (OrderStatus.PAID, OrderStatus.SHIPPED)


@router.get("/{order_id}/status")
@limiter.limit("30/minute;300/hour")
def public_order_status(
    order_id: int,
    request: Request,
    token: str = Query(..., min_length=8, max_length=64),
    db: Session = Depends(get_db),
):
    """Stato di un ordine per il compratore che ne possiede il token."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or not order.public_token:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    if not secrets.compare_digest(str(order.public_token), token):
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    return {
        "id": order.id,
        "status": order.status.value,
        "paid": order.status in PAID_STATUSES,
        "cancelled": order.status == OrderStatus.CANCELLED,
    }


@router.post("/{order_id}/checkout")
@limiter.limit("10/minute;60/hour")
def create_checkout(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Crea una Checkout Session Stripe per un ordine PENDING e restituisce
    l'URL a cui redirigere il compratore. Pubblico: l'ordine e' appena stato
    creato dal compratore."""
    from utils import stripe_client as sc

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Ordine non pagabile (gia' processato)")
    if not sc.is_configured():
        raise HTTPException(status_code=503, detail="Pagamento con carta non disponibile")
    try:
        session = sc.create_checkout_session(order)
    except sc.StripeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    order.stripe_session_id = session.id
    db.commit()
    return {"url": session.url}


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

        # Gli articoli seguono l'ordine: pagato = venduti, annullato =
        # di nuovo in vendita.
        if payload.status == OrderStatus.PAID:
            mark_sold(db, order)
        elif payload.status == OrderStatus.CANCELLED:
            release_order(db, order)

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
