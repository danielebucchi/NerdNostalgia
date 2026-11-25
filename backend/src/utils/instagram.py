"""
Instagram: i nuovi arrivi pubblicati in automatico.

- Un carosello al giorno (18:30) con fino a 10 articoli pubblicati da poco,
  i piu' cari per primi: anche nei giorni da 50 carte il profilo riceve un
  post solo.
- Una Storia per ogni articolo da almeno `instagram_story_min_price` euro,
  al massimo MAX_STORIE_GIORNO al giorno.

Usa la "Instagram API with Instagram Login" (account professionale, niente
Pagina Facebook). Configurazione: INSTAGRAM_USER_ID e INSTAGRAM_ACCESS_TOKEN
(env, dal vault di garganacl) e la spunta `instagram_enabled` in
Impostazioni. Il token dura 60 giorni: il job del lunedi' lo rinnova e
tiene quello nuovo nei settings (chiave fuori dalla SPEC, quindi non
compare in Impostazioni ne' nelle API pubbliche).

Instagram vuole JPEG raggiungibili da un URL pubblico, in proporzioni fra
4:5 e 1.91:1 per il feed: le scansioni delle carte (circa 5:7) sono piu'
strette e verrebbero rifiutate. `immagine()` le mette su una tela 4:5 (post)
o 9:16 (Storia) con titolo e prezzo; le serve /api/social/instagram/...
Ogni articolo va nel carosello una volta sola e ha al massimo una Storia
(article_metadata.instagram_carousel / instagram_story).
"""
import io
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
from sqlalchemy.orm import Session

from models.db import Article, ArticleStatus

LOGGER = logging.getLogger("instagram")

GRAPH = "https://graph.instagram.com/v23.0"
TIMEOUT = 30

CHIAVE_ACCESO = "instagram_enabled"
CHIAVE_SOGLIA = "instagram_story_min_price"
CHIAVE_TOKEN = "instagram_access_token"
CHIAVE_STORIE_OGGI = "instagram_stories_day"

MAX_CAROSELLO = 10          # il massimo che Instagram accetta in un carosello
MAX_STORIE_GIORNO = 10
FINESTRA = timedelta(days=3)  # oltre, un articolo non e' piu' un "nuovo arrivo"

POST = (1080, 1350)   # 4:5
STORIA = (1080, 1920)  # 9:16
SFONDO = (253, 246, 238)
INK = (61, 42, 92)
ROSA = (232, 121, 168)

TELEGRAM_URL = "t.me/NerdNostalgia"


class ErroreInstagram(Exception):
    pass


def _ora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _api_url() -> str:
    return (os.getenv("BASE_URL") or "https://api.nerdnostalgia.store").rstrip("/")


# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------

def _impostazioni(db: Session):
    from helpers.setting import SettingHelper
    return SettingHelper(db=db)


def _token(db: Session) -> str:
    return (_impostazioni(db).get_value(CHIAVE_TOKEN, default="") or os.getenv("INSTAGRAM_ACCESS_TOKEN", "")).strip()


def configurato(db: Session) -> bool:
    return bool(os.getenv("INSTAGRAM_USER_ID", "").strip() and _token(db))


def acceso(db: Session) -> bool:
    return (_impostazioni(db).get_value(CHIAVE_ACCESO) or "").strip().lower() == "true" and configurato(db)


def soglia_storie(db: Session) -> float:
    try:
        return float((_impostazioni(db).get_value(CHIAVE_SOGLIA) or "20").replace(",", "."))
    except ValueError:
        return 20.0


# ---------------------------------------------------------------------------
# Immagini
# ---------------------------------------------------------------------------

FONT = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",  # nel container
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",             # sul Mac
]


def _font(size: int):
    for percorso in FONT:
        if Path(percorso).exists():
            return ImageFont.truetype(percorso, size)
    return ImageFont.load_default(size=size)


def _foto(article: Article) -> Optional[Image.Image]:
    """La prima foto dell'articolo: dal disco se e' nostra, altrimenti
    scaricata."""
    from utils.storage import UPLOADS_DIR
    url = next(iter(article.images or []), None)
    if not url:
        return None
    try:
        if url.startswith("/static/"):
            percorso = (UPLOADS_DIR / url[len("/static/"):]).resolve()
            if UPLOADS_DIR.resolve() not in percorso.parents:
                return None
            img = Image.open(percorso)
        else:
            r = requests.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content))
        return ImageOps.exif_transpose(img).convert("RGB")
    except (OSError, requests.RequestException) as exc:
        LOGGER.warning("Foto dell'articolo %s non leggibile: %s", article.id, exc)
        return None


def _righe(draw: ImageDraw.ImageDraw, testo: str, font, larghezza: int, massimo: int) -> List[str]:
    parole, righe, riga = testo.split(), [], ""
    for parola in parole:
        prova = f"{riga} {parola}".strip()
        if draw.textlength(prova, font=font) <= larghezza:
            riga = prova
            continue
        if riga:
            righe.append(riga)
        riga = parola
        if len(righe) == massimo:
            break
    if riga and len(righe) < massimo:
        righe.append(riga)
    if len(righe) == massimo and " ".join(righe) != " ".join(parole):
        while righe[-1] and draw.textlength(righe[-1] + "…", font=font) > larghezza:
            righe[-1] = righe[-1][:-1]
        righe[-1] = righe[-1].rstrip() + "…"
    return righe


def _prezzo(article: Article) -> str:
    return f"{float(article.price or 0):.2f} €".replace(".", ",")


def immagine(article: Article, formato: str = "post") -> bytes:
    """JPEG pronto per Instagram: la foto riquadrata, titolo e prezzo."""
    storia = formato == "storia"
    w, h = STORIA if storia else POST
    tela = Image.new("RGB", (w, h), SFONDO)
    draw = ImageDraw.Draw(tela)
    margine = 60

    # In alto la scritta (Storia) o il sito (post), in basso titolo e prezzo,
    # in mezzo la foto, ingrandita fino a riempire lo spazio.
    if storia:
        f = _font(64)
        testo = "NUOVO ARRIVO"
        draw.text(((w - draw.textlength(testo, font=f)) / 2, 90), testo, font=f, fill=ROSA)
        alto, fascia = 200, 560
    else:
        f = _font(32)
        testo = "nerdnostalgia.store"
        draw.text(((w - draw.textlength(testo, font=f)) / 2, 34), testo, font=f, fill=INK)
        alto, fascia = 100, 270

    foto = _foto(article)
    if foto is not None:
        box_w, box_h = w - 2 * margine, h - alto - fascia - 20
        scala = min(box_w / foto.width, box_h / foto.height)
        foto = foto.resize((max(1, round(foto.width * scala)), max(1, round(foto.height * scala))), Image.LANCZOS)
        tela.paste(foto, ((w - foto.width) // 2, alto + (box_h - foto.height) // 2))

    y = h - fascia + (30 if storia else 10)
    f_titolo = _font(58 if storia else 44)
    for riga in _righe(draw, article.title or "", f_titolo, w - 2 * margine, 3 if storia else 2):
        draw.text(((w - draw.textlength(riga, font=f_titolo)) / 2, y), riga, font=f_titolo, fill=INK)
        y += f_titolo.size + 12
    f_prezzo = _font(96 if storia else 72)
    prezzo = _prezzo(article)
    draw.text(((w - draw.textlength(prezzo, font=f_prezzo)) / 2, y + 14), prezzo, font=f_prezzo, fill=ROSA)
    if storia:
        f_sito = _font(44)
        sito = "nerdnostalgia.store"
        draw.text(((w - draw.textlength(sito, font=f_sito)) / 2, h - 130), sito, font=f_sito, fill=INK)

    out = io.BytesIO()
    tela.save(out, "JPEG", quality=90)
    return out.getvalue()


def url_immagine(article: Article, formato: str) -> str:
    # Il parametro cambia quando cambia l'articolo: Instagram non deve
    # riusare un'immagine vecchia rimasta in cache.
    versione = int((article.updated_at or article.published_at or _ora()).timestamp())
    return f"{_api_url()}/api/social/instagram/{article.id}/{formato}.jpg?v={versione}"


# ---------------------------------------------------------------------------
# Didascalia
# ---------------------------------------------------------------------------

HASHTAG = {
    "pok": "#pokemon #cartepokemon #pokemontcg #pokemonita",
    "videogioc": "#retrogaming #videogiochi #retrogames",
    "console": "#retrogaming #console #retroconsole",
    "funko": "#funkopop #funko",
    "yu-gi-oh": "#yugioh #yugiohita",
    "yugioh": "#yugioh #yugiohita",
    "magic": "#mtg #magicthegathering",
    "giocattol": "#giocattolivintage #anni90",
}


def _hashtag(articoli: List[Article]) -> str:
    tag = ["#nerdnostalgia", "#collezionismo", "#vintage"]
    for a in articoli:
        nomi = []
        cat = a.category
        while cat is not None:
            nomi.append((cat.name or "").lower())
            cat = cat.parent if cat.parent_id else None
        for chiave, valore in HASHTAG.items():
            if any(chiave in n for n in nomi):
                tag += [t for t in valore.split() if t not in tag]
    return " ".join(tag[:20])


def didascalia(articoli: List[Article]) -> str:
    righe = ["🆕 Nuovi arrivi su NerdNostalgia!" if len(articoli) > 1 else "🆕 Nuovo arrivo su NerdNostalgia!", ""]
    righe += [f"▪️ {a.title} — {_prezzo(a)}" for a in articoli]
    righe += ["", "🛒 Li trovi su nerdnostalgia.store (link in bio)",
              f"💬 Le novità in tempo reale nel gruppo Telegram: {TELEGRAM_URL}", "", _hashtag(articoli)]
    return "\n".join(righe)[:2200]


# ---------------------------------------------------------------------------
# Graph API
# ---------------------------------------------------------------------------

def _chiama(metodo: str, percorso: str, token: str, **parametri) -> dict:
    parametri["access_token"] = token
    try:
        if metodo == "GET":
            r = requests.get(f"{GRAPH}/{percorso}", params=parametri, timeout=TIMEOUT)
        else:
            r = requests.post(f"{GRAPH}/{percorso}", data=parametri, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise ErroreInstagram(f"Instagram non raggiungibile: {exc}") from exc
    try:
        dati = r.json()
    except ValueError:
        dati = {}
    if r.status_code != 200 or "error" in dati:
        messaggio = (dati.get("error") or {}).get("message") or r.text[:300]
        raise ErroreInstagram(f"Instagram ha risposto {r.status_code}: {messaggio}")
    return dati


def _attendi(token: str, contenitore: str, tentativi: int = 20, pausa: float = 3.0) -> None:
    """Instagram scarica l'immagine in differita: si pubblica solo quando il
    contenitore e' FINISHED."""
    for _ in range(tentativi):
        stato = _chiama("GET", contenitore, token, fields="status_code").get("status_code")
        if stato == "FINISHED":
            return
        if stato in ("ERROR", "EXPIRED"):
            raise ErroreInstagram(f"Instagram non ha accettato il contenuto ({stato})")
        time.sleep(pausa)
    raise ErroreInstagram("Instagram non ha finito di elaborare il contenuto in tempo")


def _pubblica(token: str, contenitore: str) -> str:
    _attendi(token, contenitore)
    utente = os.environ["INSTAGRAM_USER_ID"].strip()
    return _chiama("POST", f"{utente}/media_publish", token, creation_id=contenitore)["id"]


def _contenitore(token: str, **parametri) -> str:
    utente = os.environ["INSTAGRAM_USER_ID"].strip()
    return _chiama("POST", f"{utente}/media", token, **parametri)["id"]


# ---------------------------------------------------------------------------
# Cosa pubblicare
# ---------------------------------------------------------------------------

def _candidati(db: Session) -> List[Article]:
    return (db.query(Article)
            .filter(Article.status == ArticleStatus.PUBLISHED,
                    Article.reserved_order_id.is_(None),
                    Article.quantity > 0,
                    Article.published_at >= _ora() - FINESTRA)
            .order_by(Article.published_at)
            .all())


def _segna(db: Session, article: Article, chiave: str, valore: str) -> None:
    meta = dict(article.article_metadata or {})
    meta[chiave] = valore
    article.article_metadata = meta


def da_carosello(db: Session) -> List[Article]:
    articoli = [a for a in _candidati(db)
                if a.images and float(a.price or 0) > 0
                and not (a.article_metadata or {}).get("instagram_carousel")]
    articoli.sort(key=lambda a: float(a.price or 0), reverse=True)
    return articoli[:MAX_CAROSELLO]


def _storie_oggi(db: Session) -> int:
    oggi = _ora().date().isoformat()
    valore = _impostazioni(db).get_value(CHIAVE_STORIE_OGGI, default="") or ""
    giorno, _, quante = valore.partition(":")
    return int(quante) if giorno == oggi and quante.isdigit() else 0


def da_storie(db: Session) -> List[Article]:
    soglia = soglia_storie(db)
    articoli = [a for a in _candidati(db)
                if a.images and float(a.price or 0) >= soglia
                and not (a.article_metadata or {}).get("instagram_story")]
    return articoli[:max(MAX_STORIE_GIORNO - _storie_oggi(db), 0)]


def pubblica_carosello(db: Session) -> Optional[Dict[str, object]]:
    """Il post del giorno. None se spento o se non c'e' niente di nuovo."""
    if not acceso(db):
        return None
    articoli = da_carosello(db)
    if not articoli:
        return None
    token = _token(db)
    testo = didascalia(articoli)
    if len(articoli) == 1:
        contenitore = _contenitore(token, image_url=url_immagine(articoli[0], "post"), caption=testo)
    else:
        figli = [_contenitore(token, image_url=url_immagine(a, "post"), is_carousel_item="true")
                 for a in articoli]
        for figlio in figli:
            _attendi(token, figlio)
        contenitore = _contenitore(token, media_type="CAROUSEL", children=",".join(figli), caption=testo)
    media = _pubblica(token, contenitore)
    for a in articoli:
        _segna(db, a, "instagram_carousel", media)
    db.commit()
    LOGGER.info("Instagram: carosello %s con %d articoli", media, len(articoli))
    return {"media": media, "articoli": [a.id for a in articoli]}


def pubblica_storie(db: Session) -> List[str]:
    """Le Storie dei pezzi sopra soglia non ancora annunciati."""
    if not acceso(db):
        return []
    token = _token(db)
    fatte = []
    for a in da_storie(db):
        try:
            media = _pubblica(token, _contenitore(token, media_type="STORIES",
                                                  image_url=url_immagine(a, "storia")))
        except ErroreInstagram as exc:
            LOGGER.warning("Instagram: Storia dell'articolo %s non pubblicata: %s", a.id, exc)
            continue
        _segna(db, a, "instagram_story", media)
        _impostazioni(db).upsert(CHIAVE_STORIE_OGGI, f"{_ora().date().isoformat()}:{_storie_oggi(db) + 1}")
        db.commit()
        fatte.append(media)
    if fatte:
        LOGGER.info("Instagram: %d Storie pubblicate", len(fatte))
    return fatte


def rinnova_token(db: Session) -> bool:
    """Il token vale 60 giorni e si rinnova solo se ha almeno un giorno:
    il job del lunedi' lo allunga ogni settimana."""
    if not configurato(db):
        return False
    r = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": _token(db)}, timeout=TIMEOUT)
    nuovo = r.json().get("access_token") if r.status_code == 200 else None
    if not nuovo:
        LOGGER.warning("Instagram: rinnovo del token fallito (%s)", r.status_code)
        return False
    _impostazioni(db).upsert(CHIAVE_TOKEN, nuovo)
    LOGGER.info("Instagram: token rinnovato")
    return True
