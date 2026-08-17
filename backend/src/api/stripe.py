"""
API Stripe: webhook di conferma pagamento + stato configurazione.

Il webhook e' l'unico punto affidabile per marcare un ordine PAID (il redirect
del browser non basta: puo' non avvenire). Verifica la firma, poi su
'checkout.session.completed' porta l'ordine a PAID (idempotente).
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from models.db import Order, OrderStatus, User
from utils import stripe_client as sc
from utils.session import get_db

LOGGER = logging.getLogger("stripe_api")

router = APIRouter(prefix="/api/stripe", tags=["stripe"])


@router.get("/status")
def status_check(_admin: User = Depends(require_admin)):
    return {
        "configured": sc.is_configured(),
        "test_mode": sc.is_test_mode(),
        "webhook_ready": bool(sc._webhook_secret()),
    }


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = sc.construct_event(payload, sig)
    except sc.StripeError as exc:
        LOGGER.warning("Webhook Stripe rifiutato: %s", exc)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": str(exc)})

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_id = (session.get("metadata") or {}).get("order_id") or session.get("client_reference_id")
        if order_id:
            _mark_paid(db, int(order_id), session.get("payment_intent"))

    # 200: acknowledged. Eventi non gestiti = no-op ma confermati.
    return {"received": True}


def _mark_paid(db: Session, order_id: int, payment_intent) -> None:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        LOGGER.warning("Webhook: ordine %s non trovato", order_id)
        return
    if order.status == OrderStatus.PAID:
        return  # idempotente: gia' pagato
    order.status = OrderStatus.PAID
    order.paid_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if payment_intent:
        order.stripe_payment_intent = payment_intent
    db.commit()
    LOGGER.info("Ordine %s marcato PAID via Stripe", order_id)
    try:
        from utils.email import send_order_notification
        send_order_notification(order)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Notifica ordine pagato fallita (%s): %s", order_id, exc)
