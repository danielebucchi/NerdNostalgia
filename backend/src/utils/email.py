"""
Invio email via SMTP (Gmail App Password compatibile).

Configurazione via env:
  SMTP_HOST       (default: smtp.gmail.com)
  SMTP_PORT       (default: 587)
  SMTP_USER       email mittente (es. nerdnostalgiaita@gmail.com)
  SMTP_PASSWORD   Gmail "app password" (16 char senza spazi)
  EMAIL_FROM      header From (default: SMTP_USER)
  EMAIL_TO_ADMIN  destinatario notifiche admin
                  (default: nerdnostalgiaita@gmail.com)
  EMAIL_ENABLED   '1' per abilitare l'invio (default '1')

Se le credenziali non sono configurate, log warning e ritorna False
SENZA sollevare eccezione (l'inquiry deve essere salvata comunque).
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

LOGGER = logging.getLogger("email")

DEFAULT_ADMIN_EMAIL = "nerdnostalgiaita@gmail.com"


def _config() -> dict:
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from_addr": os.getenv("EMAIL_FROM") or os.getenv("SMTP_USER", ""),
        "to_admin": os.getenv("EMAIL_TO_ADMIN", DEFAULT_ADMIN_EMAIL),
        "enabled": os.getenv("EMAIL_ENABLED", "1") == "1",
    }


def send_email(
    *,
    to: str,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> bool:
    """Invia una email. Ritorna True se inviata, False altrimenti (con log).

    Non solleva eccezione: chi chiama non deve preoccuparsi del fallimento,
    l'azione principale (es. salvataggio inquiry) prosegue comunque.
    """
    cfg = _config()
    if not cfg["enabled"]:
        LOGGER.info("Email disabilitata (EMAIL_ENABLED=0)")
        return False
    if not cfg["user"] or not cfg["password"]:
        LOGGER.warning(
            "SMTP non configurato: imposta SMTP_USER e SMTP_PASSWORD. "
            "Email non inviata a %s.", to,
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["from_addr"]
    msg["To"] = to
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(cfg["user"], cfg["password"])
            smtp.send_message(msg)
        LOGGER.info("Email inviata a %s (subject=%r)", to, subject)
        return True
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("SMTP send failed: %s", exc)
        return False


def send_inquiry_notification(
    inquiry,
    article_title: Optional[str] = None,
    article_url: Optional[str] = None,
) -> bool:
    """Notifica all'admin di una nuova richiesta dal form 'Chiedi info'."""
    cfg = _config()
    to_admin = cfg["to_admin"]

    subject_short = (
        inquiry.subject
        or (f"Info su {article_title}" if article_title else "Nuova richiesta")
    )
    article_block_text = ""
    article_block_html = ""
    if article_title:
        article_block_text = f"\nArticolo: {article_title}"
        if article_url:
            article_block_text += f"\nLink: {article_url}"
        article_block_html = (
            f"<p><strong>Articolo:</strong> {article_title}"
            + (f' (<a href="{article_url}">apri</a>)' if article_url else "")
            + "</p>"
        )

    text_body = f"""Nuova richiesta da NerdNostalgia
--------------------------------
Da: {inquiry.name} <{inquiry.email}>
{f"Tel: {inquiry.phone}" if inquiry.phone else ""}
Oggetto: {subject_short}{article_block_text}

Messaggio:
{inquiry.message}

--
Apri nell'admin: /admin/inquiries/{inquiry.id}
"""

    html_body = f"""<html><body style="font-family: sans-serif; max-width: 600px; margin: auto;">
  <h2 style="color: #e879a8;">✉ Nuova richiesta da NerdNostalgia</h2>
  <p>
    <strong>Da:</strong> {inquiry.name}
    &lt;<a href="mailto:{inquiry.email}">{inquiry.email}</a>&gt;<br>
    {f"<strong>Tel:</strong> {inquiry.phone}<br>" if inquiry.phone else ""}
    <strong>Oggetto:</strong> {subject_short}
  </p>
  {article_block_html}
  <hr>
  <p><strong>Messaggio:</strong></p>
  <pre style="white-space: pre-wrap; background: #fbf7f4; padding: 12px; border-radius: 8px;">{inquiry.message}</pre>
  <hr>
  <p style="font-size: 0.85em; color: #888;">
    Apri nell'admin: <code>/admin/inquiries/{inquiry.id}</code>
  </p>
</body></html>"""

    return send_email(
        to=to_admin,
        subject=f"[NerdNostalgia] {subject_short}",
        text_body=text_body,
        html_body=html_body,
        reply_to=inquiry.email,
    )
