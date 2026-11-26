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
anche se torna pubblicato. Nei giorni senza novita' `ripesca` (alle 13 e
alle 20) posta un articolo gia' in catalogo, "ancora disponibile": prima
quelli mai passati da Telegram, dal piu' recente; finiti quelli, quelli
postati da piu' tempo (mai prima di RIPOSTA_DOPO). Al massimo MAX_ORA messaggi l'ora: una sync
Vinted con tanti articoli nuovi non deve intasare il canale. L'invio va in
un thread: la pubblicazione non aspetta Telegram.
"""
import logging
import os
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from html import escape
from typing import Optional

import requests

LOGGER = logging.getLogger("telegram_channel")

MAX_ORA = 20
RIPOSTA_DOPO = timedelta(days=60)
CHIAVE_NOVITA_OGGI = "telegram_new_day"
ROMA = ZoneInfo("Europe/Rome")


def _adesso() -> datetime:
    return datetime.now(ROMA).replace(tzinfo=None)
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


def testo(titolo: str, prezzo: float, link: str, categoria: Optional[str], ripescato: bool = False) -> str:
    righe = [f"{'✨ Ancora disponibile: ' if ripescato else '🆕 '}<b>{escape(titolo)}</b>",
             f"💶 {prezzo:.2f} €".replace(".", ",")]
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
    meta["telegram_posted"] = True
    meta["telegram_posted_at"] = _adesso().isoformat(timespec="seconds")
    article.article_metadata = meta
    db.commit()
    _segna_novita_oggi(db)
    threading.Thread(target=_invia, args=(_messaggio(article),), daemon=True).start()
    return True


def _messaggio(article, ripescato: bool = False) -> str:
    cat = article.category
    categoria = (f"{cat.parent.name} › {cat.name}" if cat is not None and cat.parent_id and cat.parent
                 else (cat.name if cat is not None else None))
    return testo(article.title, float(article.price or 0), f"{_site_url()}/articles/{article.id}",
                 categoria, ripescato)


def _segna_novita_oggi(db) -> None:
    from helpers.setting import SettingHelper
    SettingHelper(db=db).upsert(CHIAVE_NOVITA_OGGI, _adesso().date().isoformat())


def da_ripescare(db):
    """L'articolo in vendita da riproporre: mai passato da Telegram (dal piu'
    recente), altrimenti quello postato da piu' tempo, se oltre RIPOSTA_DOPO."""
    from models.db import Article, ArticleStatus
    articoli = (db.query(Article)
                .filter(Article.status == ArticleStatus.PUBLISHED,
                        Article.reserved_order_id.is_(None),
                        Article.quantity > 0,
                        Article.price > 0)
                .order_by(Article.published_at.desc(), Article.id.desc())
                .all())
    mai = [a for a in articoli if not (a.article_metadata or {}).get("telegram_posted")]
    if mai:
        return mai[0]
    limite = (_adesso() - RIPOSTA_DOPO).isoformat(timespec="seconds")
    postati = [(((a.article_metadata or {}).get("telegram_posted_at") or ""), a) for a in articoli]
    postati = [(quando, a) for quando, a in postati if quando < limite]
    return min(postati, key=lambda qa: qa[0])[1] if postati else None


def ripesca(db) -> Optional[int]:
    """Il giro delle 13 e delle 20: se oggi non e' uscito nessun nuovo arrivo,
    riproponi un articolo del catalogo. Torna l'id dell'articolo postato."""
    from helpers.setting import SettingHelper
    if not configurato():
        return None
    if SettingHelper(db=db).get_value(CHIAVE_NOVITA_OGGI, default="") == _adesso().date().isoformat():
        return None
    article = da_ripescare(db)
    if article is None:
        return None
    meta = dict(article.article_metadata or {})
    meta["telegram_posted"] = True
    meta["telegram_posted_at"] = _adesso().isoformat(timespec="seconds")
    article.article_metadata = meta
    db.commit()
    _invia(_messaggio(article, ripescato=True))
    LOGGER.info("Telegram: ripescato l'articolo %s", article.id)
    return article.id
