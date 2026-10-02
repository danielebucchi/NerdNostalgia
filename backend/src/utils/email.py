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


def _whatsapp_url(phone: Optional[str], default_text: str = "") -> Optional[str]:
    """Converte un numero di telefono in URL wa.me.

    Regole conservative: normalizza solo se il numero sembra italiano
    (10 cifre che cominciano con 3 = cellulare; o 12 cifre che cominciano
    con 39). Per altri formati restituisce None così l'email mostra solo
    il classico tel: link senza promettere WhatsApp che potrebbe non
    esistere.
    """
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not digits:
        return None
    # 00 prefix → toglilo
    if digits.startswith("00"):
        digits = digits[2:]
    # Cellulare italiano "333 1234567" → prefix 39
    if len(digits) == 10 and digits.startswith("3"):
        digits = "39" + digits
    # 12 cifre con prefix 39 → ok
    if len(digits) == 12 and digits.startswith("39"):
        url = f"https://wa.me/{digits}"
        if default_text:
            from urllib.parse import quote
            url += f"?text={quote(default_text)}"
        return url
    # Numero non riconosciuto come italiano: prudente, no WA
    return None


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


def _site_url() -> str:
    """URL pubblico del sito, per costruire i link agli articoli."""
    return (os.getenv("SITE_PUBLIC_URL") or "https://nerdnostalgia.store").rstrip("/")


def send_order_notification(order) -> bool:
    """Notifica all'admin che un ordine e' stato PAGATO: dati compratore,
    articoli e tutto il necessario per comprare l'etichetta.

    Parte UNA volta sola, all'incasso. Prima ne partivano due (creazione +
    pagamento) e si somigliavano troppo per distinguerle a colpo d'occhio.
    Gli ordini creati ma mai pagati restano visibili in /admin/ordini:
    non c'e' niente da fare finche' non arrivano i soldi.
    """
    cfg = _config()
    to_admin = cfg["to_admin"]

    items_lines: list[str] = []
    items_html: list[str] = []
    for it in order.items:
        line = f"  - {it.title_snapshot} × {it.quantity} → € {float(it.price_snapshot):.2f}"
        items_lines.append(line)
        # Link all'articolo: serve a ritrovarlo subito per prepararlo
        link = f"{_site_url()}/articles/{it.article_id}" if it.article_id else None
        if link:
            items_lines.append(f"    {link}")
        items_html.append(
            f"<li><strong>{it.title_snapshot}</strong> × {it.quantity}"
            f" → € {float(it.price_snapshot):.2f}"
            + (f"<br><a href='{link}' style='font-size:0.85em;'>{link}</a>" if link else "")
            + "</li>"
        )

    wa_url = _whatsapp_url(
        order.buyer_phone,
        default_text=f"Ciao {order.buyer_name.split()[0] if order.buyer_name else ''}, "
        f"ti scrivo da NerdNostalgia per il tuo ordine #{order.id}.",
    )
    text_body = f"""Ordine #{order.id} PAGATO — {order.buyer_name}
==========================================

Compratore
----------
{order.buyer_name}
Email: {order.buyer_email}
{f"Tel:   {order.buyer_phone}" if order.buyer_phone else ""}
{f"WhatsApp: {wa_url}" if wa_url else ""}

{"Ritiro al locker InPost" if order.inpost_point_id else "Spedizione a"}
-----------------------
{f'{order.inpost_point_name or "Locker InPost"} (codice {order.inpost_point_id})' + chr(10) if order.inpost_point_id else ""}{order.buyer_name}
{order.ship_street}
{order.ship_postal_code} {order.ship_city}{f" ({order.ship_province})" if order.ship_province else ""}
{order.ship_country}

Articoli
--------
{chr(10).join(items_lines)}

Totali
------
Subtotale:  € {float(order.subtotal):.2f}
Spedizione: € {float(order.shipping_total):.2f}{f" (di cui assicurazione € {float(order.insurance_fee):.2f})" if order.insured and order.insurance_fee else " — ASSICURATA" if order.insured else ""}
TOTALE:     € {float(order.grand_total):.2f} {order.currency}

{f"Note: {order.notes}" if order.notes else ""}

Crea la spedizione su Packlink: https://pro.packlink.it/private/shipments/new

Dati destinatario da incollare
------------------------------
Nome:      {order.buyer_name}
Indirizzo: {order.ship_street}
CAP:       {order.ship_postal_code}
Citta':    {order.ship_city}
Provincia: {order.ship_province or "-"}
Paese:     {order.ship_country}
Telefono:  {order.buyer_phone or "NON FORNITO"}
Email:     {order.buyer_email}
Assicurazione: {"SI - valore " + f"{float(order.subtotal):.2f} EUR" if order.insured else "no"}

Pagamento incassato. Dettaglio ordine: /admin/ordini/{order.id}
"""

    html_body = f"""<html><body style="font-family: sans-serif; max-width: 640px; margin: auto;">
  <h2 style="color: #e879a8;">🛒 Nuovo ordine #{order.id}</h2>

  <h3 style="color:#3d2a5c; border-bottom: 1px solid #eee; padding-bottom: 4px;">Compratore</h3>
  <p>
    <strong>{order.buyer_name}</strong><br>
    Email: <a href="mailto:{order.buyer_email}">{order.buyer_email}</a><br>
    {f"Tel: <a href='tel:{order.buyer_phone}'>{order.buyer_phone}</a><br>" if order.buyer_phone else ""}
  </p>
  <!-- Bottoni contatto rapido: tap-to-mail / tap-to-call / WhatsApp -->
  <div style="margin: 10px 0 16px;">
    <a href="mailto:{order.buyer_email}?subject=Ordine%20%23{order.id}%20NerdNostalgia"
       style="display:inline-block; background:#a890d8; color:white; padding:8px 14px; border-radius:999px; text-decoration:none; font-weight:bold; font-size:0.85em; margin-right:6px; margin-bottom:6px;">
      ✉ Email
    </a>
    {f'''<a href="tel:{order.buyer_phone}"
       style="display:inline-block; background:#7dd3c0; color:white; padding:8px 14px; border-radius:999px; text-decoration:none; font-weight:bold; font-size:0.85em; margin-right:6px; margin-bottom:6px;">
      📞 Chiama
    </a>''' if order.buyer_phone else ''}
    {f'''<a href="{wa_url}" target="_blank"
       style="display:inline-block; background:#25D366; color:white; padding:8px 14px; border-radius:999px; text-decoration:none; font-weight:bold; font-size:0.85em; margin-right:6px; margin-bottom:6px;">
      💬 WhatsApp
    </a>''' if wa_url else ''}
  </div>

  <h3 style="color:#3d2a5c; border-bottom: 1px solid #eee; padding-bottom: 4px;">{"Ritiro al locker InPost" if order.inpost_point_id else "Spedizione a"}</h3>
  <address style="background:#fbf7f4; padding:10px 14px; border-radius:8px; font-style:normal;">
    {f'<strong>{order.inpost_point_name or "Locker InPost"}</strong><br><code style="background:#eee; padding:1px 5px; border-radius:4px;">{order.inpost_point_id}</code><br>' if order.inpost_point_id else ""}
    <strong>{order.buyer_name}</strong><br>
    {order.ship_street}<br>
    {order.ship_postal_code} {order.ship_city}{f" ({order.ship_province})" if order.ship_province else ""}<br>
    {order.ship_country}
  </address>

  <h3 style="color:#3d2a5c; border-bottom: 1px solid #eee; padding-bottom: 4px;">Articoli</h3>
  <ul>
    {''.join(items_html)}
  </ul>

  <table style="margin-top:12px;">
    <tr><td>Subtotale</td><td style="text-align:right; padding-left:24px;">€ {float(order.subtotal):.2f}</td></tr>
    <tr>
      <td>Spedizione{' <strong style="color:#7dd1b8;">🛡 assicurata</strong>' if order.insured else ''}</td>
      <td style="text-align:right; padding-left:24px;">€ {float(order.shipping_total):.2f}</td>
    </tr>
    <tr style="font-weight:bold; font-size:1.1em; color:#e879a8;">
      <td>TOTALE</td>
      <td style="text-align:right; padding-left:24px;">€ {float(order.grand_total):.2f} {order.currency}</td>
    </tr>
  </table>

  {f'<h3 style="color:#3d2a5c;">Note compratore</h3><pre style="white-space:pre-wrap; background:#fbf7f4; padding:12px; border-radius:8px;">{order.notes}</pre>' if order.notes else ""}

  <hr>
  <h3 style="color:#3d2a5c;">Spedizione</h3>
  <p>
    <a href="https://pro.packlink.it/private/shipments/new"
       style="display:inline-block; background:#7dd1b8; color:#15322a; padding:10px 18px; border-radius:999px; text-decoration:none; font-weight:bold;">
      📦 Crea la spedizione su Packlink
    </a>
  </p>
  <p style="font-size:0.85em; color:#888; margin-top:-4px;">
    Packlink non accetta i dati dal link: il riquadro qui sotto è fatto per
    essere selezionato e incollato campo per campo.
  </p>
  <pre style="background:#fbf7f4; border:1px solid #e7e0f0; border-radius:8px; padding:12px; font-size:0.85em; line-height:1.6; white-space:pre-wrap; color:#3d2a5c;">Nome:      {order.buyer_name}
Indirizzo: {order.ship_street}
CAP:       {order.ship_postal_code}
Città:     {order.ship_city}
Provincia: {order.ship_province or "-"}
Paese:     {order.ship_country}
Telefono:  {order.buyer_phone or "NON FORNITO"}
Email:     {order.buyer_email}</pre>
  {f'<p style="background:#e0f5ec; border-left:3px solid #7dd1b8; padding:8px 12px; font-size:0.9em;">🛡 <strong>Spedizione assicurata</strong> — il compratore ha pagato il premio ({float(order.insurance_fee):.2f} €). Dichiara un valore di <strong>{float(order.subtotal):.2f} €</strong> quando compri l&apos;etichetta.</p>' if order.insured else '<p style="font-size:0.85em; color:#888;">Spedizione non assicurata: il compratore non l&apos;ha richiesta.</p>'}
  <p style="font-size: 0.85em; color: #888;">
    Pagamento incassato. Dettaglio ordine:
    <code>/admin/ordini/{order.id}</code>
  </p>
</body></html>"""

    return send_email(
        to=to_admin,
        subject=(
            f"[NerdNostalgia] Ordine #{order.id} PAGATO — "
            f"{order.buyer_name} — € {float(order.grand_total):.2f}"
        ),
        text_body=text_body,
        html_body=html_body,
        reply_to=order.buyer_email,
    )


def send_order_confirmation(order) -> bool:
    """Conferma d'ordine al COMPRATORE, mandata quando il pagamento risulta
    incassato.

    Finora riceveva solo una conferma dentro PayPal: niente che gli dicesse
    cosa ha comprato, da chi e a chi scrivere se qualcosa non va. Teniamo
    `reply_to` sulla nostra casella, cosi' rispondendo scrive direttamente
    a noi.
    """
    cfg = _config()

    items_lines: list[str] = []
    items_html: list[str] = []
    for it in order.items:
        items_lines.append(
            f"  - {it.title_snapshot} × {it.quantity} → € {float(it.price_snapshot):.2f}"
        )
        link = f"{_site_url()}/articles/{it.article_id}" if it.article_id else None
        items_html.append(
            f"<li><strong>{it.title_snapshot}</strong> × {it.quantity}"
            f" → € {float(it.price_snapshot):.2f}"
            + (f"<br><a href='{link}' style='font-size:0.85em;'>rivedi l&apos;articolo</a>" if link else "")
            + "</li>"
        )

    nome = (order.buyer_name or "").split()[0] if order.buyer_name else ""
    saluto = f"Ciao {nome}," if nome else "Ciao,"
    assicurata = bool(order.insured)

    consegna_txt = (
        f"Ritiri al locker InPost {order.inpost_point_name or ''} "
        f"(codice {order.inpost_point_id})"
        if order.inpost_point_id
        else "Spedizione all'indirizzo che hai indicato"
    )

    text_body = f"""{saluto}

grazie! Ho ricevuto il tuo pagamento e il tuo ordine #{order.id} e' confermato.

Cosa hai preso
--------------
{chr(10).join(items_lines)}

Totali
------
Subtotale:  EUR {float(order.subtotal):.2f}
Spedizione: EUR {float(order.shipping_total):.2f}{" (assicurata)" if assicurata else ""}
TOTALE:     EUR {float(order.grand_total):.2f}

Consegna
--------
{consegna_txt}
{order.ship_street}
{order.ship_postal_code} {order.ship_city}{f" ({order.ship_province})" if order.ship_province else ""}

Preparo il pacco e ti scrivo appena spedisco.
Se qualcosa non torna, rispondi a questa email: la leggo io.

Nerd.Nostalgia
{_site_url()}
"""

    html_body = f"""<html><body style="font-family: sans-serif; max-width: 640px; margin: auto; color:#3d2a5c;">
  <h2 style="color: #e879a8;">Grazie {nome}! Ordine #{order.id} confermato</h2>
  <p>Ho ricevuto il tuo pagamento. Preparo il pacco e ti scrivo appena spedisco.</p>

  <h3 style="border-bottom:1px solid #eee; padding-bottom:4px;">Cosa hai preso</h3>
  <ul>{''.join(items_html)}</ul>

  <table style="margin-top:12px;">
    <tr><td>Subtotale</td><td style="text-align:right; padding-left:24px;">€ {float(order.subtotal):.2f}</td></tr>
    <tr>
      <td>Spedizione{' <strong style="color:#7dd1b8;">assicurata</strong>' if assicurata else ''}</td>
      <td style="text-align:right; padding-left:24px;">€ {float(order.shipping_total):.2f}</td>
    </tr>
    <tr style="font-weight:bold; font-size:1.1em; color:#e879a8;">
      <td>TOTALE</td>
      <td style="text-align:right; padding-left:24px;">€ {float(order.grand_total):.2f}</td>
    </tr>
  </table>

  <h3 style="border-bottom:1px solid #eee; padding-bottom:4px; margin-top:20px;">Consegna</h3>
  <address style="background:#fbf7f4; padding:10px 14px; border-radius:8px; font-style:normal;">
    {consegna_txt}<br>
    {order.ship_street}<br>
    {order.ship_postal_code} {order.ship_city}{f" ({order.ship_province})" if order.ship_province else ""}
  </address>

  <p style="margin-top:20px;">
    Se qualcosa non torna, <strong>rispondi a questa email</strong>: la leggo io.
  </p>
  <p style="color:#888; font-size:0.9em;">
    Nerd.Nostalgia · <a href="{_site_url()}">{_site_url()}</a>
  </p>
</body></html>"""

    return send_email(
        to=order.buyer_email,
        subject=f"Grazie! Il tuo ordine #{order.id} su Nerd.Nostalgia è confermato",
        text_body=text_body,
        html_body=html_body,
        reply_to=cfg["to_admin"],
    )

