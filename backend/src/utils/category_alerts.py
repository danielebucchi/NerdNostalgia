"""
Notifiche "nuovo arrivo" agli iscritti di category_alerts.

Best-effort: mai sollevare verso il chiamante — la pubblicazione di un
articolo non deve fallire perche' l'SMTP e' giu'. Il token di disiscrizione
e' HMAC(JWT_SECRET_KEY, email) e vale per TUTTE le iscrizioni dell'email
(un solo click e non ricevi piu' nulla, niente gestione granulare).
"""
import hashlib
import hmac
import logging
import os
from typing import Iterable, List
from urllib.parse import quote

from sqlalchemy.orm import Session

from models.db import Article, CategoryAlert
from utils.email import send_email

LOGGER = logging.getLogger("category_alerts")


def _secret() -> bytes:
    return os.getenv("JWT_SECRET_KEY", "dev-secret-change-me").encode()


def unsubscribe_token(email: str) -> str:
    digest = hmac.new(
        _secret(), f"alerts:{email.lower().strip()}".encode(), hashlib.sha256,
    ).hexdigest()
    return digest[:32]


def verify_unsubscribe_token(email: str, token: str) -> bool:
    return hmac.compare_digest(unsubscribe_token(email), token)


def _site_url() -> str:
    return (
        os.getenv("SITE_PUBLIC_URL")
        or os.getenv("NEXT_PUBLIC_SITE_URL")
        or "https://nerdnostalgia.store"
    ).rstrip("/")


def _api_url() -> str:
    return (os.getenv("BASE_URL") or "http://localhost:7373").rstrip("/")


def _recipients_for(db: Session, article: Article) -> List[str]:
    """Email iscritte alla categoria dell'articolo, al suo parent, o a tutte
    (category_id NULL). Dedup case-insensitive."""
    category_ids: List[int] = []
    if article.category_id is not None:
        category_ids.append(article.category_id)
        if article.category is not None and article.category.parent_id is not None:
            category_ids.append(article.category.parent_id)

    query = db.query(CategoryAlert).filter(
        CategoryAlert.category_id.is_(None)
        if not category_ids
        else (
            CategoryAlert.category_id.is_(None)
            | CategoryAlert.category_id.in_(category_ids)
        )
    )
    seen: set = set()
    out: List[str] = []
    for sub in query.all():
        key = sub.email.lower().strip()
        if key not in seen:
            seen.add(key)
            out.append(sub.email)
    return out


def notify_new_article(db: Session, article: Article) -> int:
    """Manda l'avviso "nuovo arrivo" agli iscritti pertinenti.
    Ritorna il numero di email inviate. Non solleva mai."""
    try:
        recipients = _recipients_for(db, article)
    except Exception:  # noqa: BLE001
        LOGGER.exception("Lookup iscritti fallito per articolo %s", article.id)
        return 0
    if not recipients:
        return 0

    article_url = f"{_site_url()}/articles/{article.id}"
    price = f"{article.price} {article.currency or 'EUR'}"
    category_name = article.category.name if article.category else None

    sent = 0
    for email_addr in recipients:
        token = unsubscribe_token(email_addr)
        unsub_url = (
            f"{_api_url()}/api/alerts/unsubscribe"
            f"?email={quote(email_addr)}&token={token}"
        )
        subject = f"✨ Nuovo arrivo: {article.title}"
        text_lines = [
            f"E' arrivato un nuovo articolo{f' in {category_name}' if category_name else ''}!",
            "",
            article.title,
            f"Prezzo: {price}",
            "",
            f"Guardalo qui: {article_url}",
            "",
            "--",
            f"Non vuoi piu' ricevere questi avvisi? {unsub_url}",
        ]
        html = f"""
        <div style="font-family:sans-serif;max-width:560px">
          <h2 style="color:#3d2a5c">✨ Nuovo arrivo{f" in {category_name}" if category_name else ""}</h2>
          <p style="font-size:16px"><strong>{article.title}</strong></p>
          <p style="font-size:15px">Prezzo: <strong>{price}</strong></p>
          <p><a href="{article_url}"
                style="display:inline-block;background:#e879a8;color:#fff;
                       padding:10px 22px;border-radius:999px;text-decoration:none;
                       font-weight:bold">Guardalo sul sito</a></p>
          <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
          <p style="font-size:12px;color:#888">
            Ricevi questa mail perche' ti sei iscritto agli avvisi di NerdNostalgia.<br>
            <a href="{unsub_url}" style="color:#888">Disiscriviti</a>
          </p>
        </div>
        """
        try:
            if send_email(
                to=email_addr,
                subject=subject,
                text_body="\n".join(text_lines),
                html_body=html,
            ):
                sent += 1
        except Exception:  # noqa: BLE001
            LOGGER.exception("Invio avviso a %s fallito", email_addr)
    LOGGER.info(
        "Avvisi nuovo arrivo: articolo=%s inviate=%d/%d",
        article.id, sent, len(recipients),
    )
    return sent


def notify_many(db: Session, articles: Iterable[Article]) -> int:
    total = 0
    for a in articles:
        total += notify_new_article(db, a)
    return total
