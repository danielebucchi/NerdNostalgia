"""
Invio email fuori dalla richiesta HTTP.

L'SMTP di Gmail ci mette qualche secondo a rispondere e, finche' il backend
aspetta, aspetta anche il browser di chi ha premuto il bottone: la
registrazione impiegava 8 secondi, tutti spesi a guardare uno spinner. Il
messaggio non fa parte della risposta, quindi non deve farla aspettare.

Due accortezze che sembrano dettagli ma non lo sono:

* Ogni invio gira in un thread con la SUA sessione di database e ricarica
  l'oggetto per id. La sessione della richiesta viene chiusa appena la
  risposta parte, e riusarla dopo darebbe DetachedInstanceError alla prima
  relazione letta (order.items, per dirne una).
* Se le email sono spente non si apre nessun thread: nei test questo evita
  che un thread vada a cercare il database di produzione mentre la suite usa
  quello in memoria.

Gli errori restano nei log e basta: un'email non partita non deve mai far
fallire un ordine gia' pagato.
"""
import logging
import threading
from typing import Callable

LOGGER = logging.getLogger("mailer")


def _emails_enabled() -> bool:
    from utils.email import _config
    try:
        return bool(_config()["enabled"])
    except Exception:  # noqa: BLE001
        return False


def _run_detached(job: Callable[[], None], descrizione: str) -> None:
    def wrapper() -> None:
        try:
            job()
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Invio email fallito (%s): %s", descrizione, exc)

    threading.Thread(target=wrapper, name=f"mail-{descrizione}", daemon=True).start()


def _with_order(order_id: int, invia: Callable, descrizione: str) -> None:
    if not _emails_enabled():
        return

    def job() -> None:
        from models.db import Order
        from utils.session import SessionLocal
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order is None:
                LOGGER.warning("Ordine %s sparito prima dell'invio", order_id)
                return
            invia(order)
        finally:
            db.close()

    _run_detached(job, f"{descrizione}-{order_id}")


def order_notification(order_id: int) -> None:
    """All'admin: cosa preparare e spedire."""
    from utils.email import send_order_notification
    _with_order(order_id, send_order_notification, "ordine-admin")


def order_confirmation(order_id: int) -> None:
    """Al compratore: conferma d'ordine."""
    from utils.email import send_order_confirmation
    _with_order(order_id, send_order_confirmation, "ordine-cliente")


def shipping_notice(order_id: int) -> None:
    """Al compratore: il pacco e' partito, con il tracking."""
    from utils.email import send_shipping_notice
    _with_order(order_id, send_shipping_notice, "spedizione")


def welcome(user_id: int) -> None:
    """A chi si e' appena registrato."""
    if not _emails_enabled():
        return

    def job() -> None:
        from models.db import User
        from utils.session import SessionLocal
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                return
            from utils.email import send_welcome_email
            send_welcome_email(user)
        finally:
            db.close()

    _run_detached(job, f"benvenuto-{user_id}")
