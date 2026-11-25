"""
Canale Telegram dei nuovi arrivi.

Ogni articolo pubblicato sul sito finisce nel canale: titolo, prezzo e
link. La foto la mostra Telegram dall'anteprima della pagina (og:image),
cosi' non serve mandarla (e i .webp come foto Telegram non li prende).

Configurazione (env, dal vault di garganacl): TELEGRAM_BOT_TOKEN, il bot
amministratore del canale, e TELEGRAM_CHANNEL_ID ("@nomecanale" o l'id
numerico). Senza, non fa niente. Se la chat e' un gruppo con gli argomenti,
TELEGRAM_TOPIC_ID e' l'id dell'argomento "Nuovi arrivi": il numero in fondo
al link di un messaggio dell'argomento (t.me/gruppo/<id>/...). Vuoto = la
chat principale.

Un articolo si annuncia una volta sola (article_metadata.telegram_posted),
anche se torna pubblicato. Al massimo MAX_ORA messaggi l'ora: una sync
Vinted con tanti articoli nuovi non deve intasare il canale. L'invio va in
un thread: la pubblicazione non aspetta Telegram.
"""
import logging
import os
import threading
import time
from collections import deque
from html import escape
from typing import Optional

import requests

LOGGER = logging.getLogger("telegram_channel")

MAX_ORA = 20
TIMEOUT = 10
_inviati: deque = deque()
_lock = threading.Lock()


def configurato() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHANNEL_ID"))


def _site_url() -> str:
    return (os.getenv("SITE_PUBLIC_URL") or os.getenv("NEXT_PUBLIC_SITE_URL")
            or "https://nerdnostalgia.store").rstrip("/")


def _posto_libero() -> bool:
    ora = time.time()
    with _lock:
        while _inviati and ora - _inviati[0] > 3600:
            _inviati.popleft()
        if len(_inviati) >= MAX_ORA:
            return False
        _inviati.append(ora)
        return True


def testo(titolo: str, prezzo: float, link: str, categoria: Optional[str]) -> str:
    righe = [f"🆕 <b>{escape(titolo)}</b>", f"💶 {prezzo:.2f} €".replace(".", ",")]
    if categoria:
        righe.append(f"🏷 {escape(categoria)}")
    righe.append(f'👉 <a href="{escape(link)}">Vedi sul sito</a>')
    return "\n".join(righe)


def payload(messaggio: str) -> dict:
    dati = {"chat_id": os.environ["TELEGRAM_CHANNEL_ID"], "text": messaggio,
            "parse_mode": "HTML", "link_preview_options": {"prefer_large_media": True}}
    argomento = (os.getenv("TELEGRAM_TOPIC_ID") or "").strip()
    if argomento.isdigit():
        dati["message_thread_id"] = int(argomento)
    return dati


def _invia(messaggio: str) -> None:
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
            json=payload(messaggio), timeout=TIMEOUT,
        )
        if r.status_code != 200:
            LOGGER.warning("Telegram ha rifiutato l'annuncio (%s): %s", r.status_code, r.text[:300])
    except requests.RequestException as exc:
        LOGGER.warning("Telegram non raggiungibile: %s", exc)


def annuncia(db, article) -> bool:
    """Annuncia l'articolo nel canale. True se l'annuncio e' partito."""
    if not configurato():
        return False
    meta = dict(article.article_metadata or {})
    if meta.get("telegram_posted"):
        return False
    if not _posto_libero():
        LOGGER.info("Canale Telegram: tetto di %d annunci l'ora, articolo %s saltato", MAX_ORA, article.id)
        return False
    cat = article.category
    categoria = (f"{cat.parent.name} › {cat.name}" if cat is not None and cat.parent_id and cat.parent
                 else (cat.name if cat is not None else None))
    messaggio = testo(article.title, float(article.price or 0), f"{_site_url()}/articles/{article.id}", categoria)
    meta["telegram_posted"] = True
    article.article_metadata = meta
    db.commit()
    threading.Thread(target=_invia, args=(messaggio,), daemon=True).start()
    return True
