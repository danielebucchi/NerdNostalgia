"""
API PayPal: creazione ordine, cattura e webhook.

Il compratore non e' autenticato, quindi ogni rotta parte dal NOSTRO ordine e
ne ricontrolla lo stato: si paga solo cio' che e' ancora PENDING, e l'importo
lo decide il server (mai il browser).

NB: NIENTE `from __future__ import annotations` (vedi api/orders.py).
"""
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from models.db import Order, OrderStatus
from utils import paypal_client as pp
from utils.limiter import limiter
from utils.session import get_db

LOGGER = logging.getLogger("paypal_api")

router = APIRouter(prefix="/api/paypal", tags=["paypal"])


def _site_url() -> str:
    return (os.getenv("SITE_PUBLIC_URL") or "http://localhost:3737").rstrip("/")


@router.get("/config")
def config():
    """Dati pubblici per caricare l'SDK nel browser. Il client id e' pubblico
    per definizione; tenerlo qui invece che in una NEXT_PUBLIC_* evita di
    ricostruire il frontend per cambiarlo o per passare da sandbox a live."""
    return pp.public_config()


def _payable_order(order_id: int, db: Session) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=400, detail="Ordine non pagabile (già processato)"
        )
    return order


@router.post("/orders/{order_id}")
@limiter.limit("10/minute;60/hour")
def create_paypal_order(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Crea l'ordine su PayPal e restituisce il suo id al bottone."""
    if not pp.is_configured():
        raise HTTPException(status_code=503, detail="PayPal non disponibile")
    order = _payable_order(order_id, db)
    try:
        created = pp.create_order(order, _site_url())
    except pp.PaypalError as exc:
        LOGGER.warning("Creazione ordine PayPal fallita (%s): %s", order_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    order.paypal_order_id = created.get("id")
    db.commit()
    return {"id": created.get("id")}


@router.post("/orders/{order_id}/capture")
@limiter.limit("10/minute;60/hour")
def capture_paypal_order(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Incassa dopo l'approvazione nel popup e porta l'ordine a PAID."""
    if not pp.is_configured():
        raise HTTPException(status_code=503, detail="PayPal non disponibile")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")
    # Gia' pagato: la cattura e' arrivata prima per webhook. Non e' un errore,
    # il compratore deve vedere comunque la conferma.
    if order.status == OrderStatus.PAID:
        return {"status": "COMPLETED", "already_paid": True}
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Ordine non pagabile")
    if not order.paypal_order_id:
        raise HTTPException(status_code=400, detail="Nessun pagamento PayPal avviato")

    try:
        captured = pp.capture_order(order.paypal_order_id)
    except pp.PaypalError as exc:
        LOGGER.warning("Cattura PayPal fallita (%s): %s", order_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not pp.is_completed(captured):
        raise HTTPException(
            status_code=402,
            detail=f"Pagamento non completato ({captured.get('status')})",
        )

    _mark_paid(db, order, pp.capture_id_from(captured))
    return {"status": "COMPLETED"}


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """Rete di sicurezza: se il browser muore fra approvazione e cattura,
    l'ordine viene marcato pagato comunque."""
    raw = (await request.body()).decode("utf-8", errors="replace")
    if not pp.verify_webhook(dict(request.headers), raw):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "firma non valida"},
        )

    event = __import__("json").loads(raw)
    if event.get("event_type") == "PAYMENT.CAPTURE.COMPLETED":
        resource = event.get("resource") or {}
        # custom_id lo abbiamo messo noi alla creazione: e' il nostro order id
        raw_id = resource.get("custom_id") or ""
        if raw_id.isdigit():
            order = db.query(Order).filter(Order.id == int(raw_id)).first()
            if order and order.status == OrderStatus.PENDING:
                _mark_paid(db, order, resource.get("id"))

    return {"received": True}


def _mark_paid(db: Session, order: Order, capture_id) -> None:
    order.status = OrderStatus.PAID
    order.paid_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if capture_id:
        order.paypal_capture_id = capture_id
    db.commit()
    # I pezzi passano da "prenotati" a VENDUTI
    from helpers.reservation import mark_sold
    mark_sold(db, order)
    LOGGER.info("Ordine %s marcato PAID via PayPal", order.id)
    try:
        from utils import mailer
        mailer.order_notification(order.id)   # a noi: cosa preparare e spedire
        mailer.order_confirmation(order.id)   # al compratore: conferma d'ordine
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Notifica ordine pagato fallita (%s): %s", order.id, exc)
