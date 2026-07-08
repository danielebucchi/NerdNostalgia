"""
Sync service Vinted → NerdNostalgia.

Pipeline:
  1) Legge vinted_settings (user_id, enabled)
  2) Fetcha gli items del profilo (utils.vinted_client, Playwright headless)
  3) Filtra per keyword NerdNostalgia (NN_KEYWORDS)
  4) Auto-detect categoria via CATEGORY_RULES (titolo + descrizione)
  5) Crea Article PUBLISHED (o aggiorna esistente)
  6) Scarica foto in WebP + thumbnail locale
  7) Cancella articoli non piu' visti su Vinted (safety: min 10 fetched)
  8) Scrive vinted_sync_logs con counters
"""
from __future__ import annotations

import datetime as _dt
import io
import logging
import re
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List, Optional

from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from models.db import (
    Article,
    ArticleCondition,
    ArticleStatus,
    Category,
    User,
    VintedSettings,
    VintedStatus,
    VintedSyncLog,
)
from utils.storage import (
    ARTICLES_UPLOADS_DIR,
    LARGE_MAX_WIDTH,
    THUMB_MAX_WIDTH,
    WEBP_QUALITY,
    public_url,
)
from utils.vinted_client import (
    VintedClientError,
    VintedItem,
    download_photo,
    fetch_user_items,
)

LOGGER = logging.getLogger("vinted_sync")

# Keyword di interesse NerdNostalgia. Cerco nel branch_title (se Vinted lo
# espone) E nel titolo/descrizione (Vinted spesso nel listing del profilo
# NON include catalog_id, solo titolo+prezzo+foto).
NN_KEYWORDS = (
    # Console / piattaforme
    "gameboy", "game boy", "gba", "nds", "3ds", "switch", "ps1", "ps2", "ps3",
    "ps4", "ps5", "psp", "psvita", "ps vita", "playstation", "xbox",
    "nintendo", "sega", "dreamcast", "saturn", "n64", "snes", "wii",
    "atari", "megadrive", "mega drive",
    # Categorie generiche videogiochi/elettronica
    "videogioco", "videogiochi", "videogame", "console", "joypad", "controller",
    "elettronica",
    # Carte
    "pokemon", "pokémon", "carte", "carta", "card", "tcg", "lorcana",
    "magic", "mtg", "yu-gi-oh", "yugioh", "one piece", "dragon ball",
    "dragonball",
    # Collezionismo / nerdate
    "collezionism", "funko", "bitty pop", "action figure", "figurine",
    "modellini", "lego", "playmobil", "kinder", "sorpresa", "stickers",
    "spilla", "spille", "poster",
    # Brand/franchise nerd
    "mario", "zelda", "link", "metroid", "kirby", "sonic", "tetris",
    "stranger things", "marvel", "harry potter", "disney", "studio ghibli",
    "naruto", "dragonball", "anime", "manga", "fumetto", "fumetti",
    "lucca comics", "comicon",
    # Termini specifici
    "console retro", "vintage", "console portatile",
)


# ─────────────────────────────────────────────────────────────────────────
# Exclusion list: se una di queste parole compare nel TITOLO l'articolo
# viene rifiutato senza nemmeno guardare le keyword positive.
# Pensata per cose chiaramente non-nerd che potrebbero passare il filtro
# generico per via di parole comuni nella description (es. "gift card"
# che fa matchare "card", o "vintage" usato come buzzword).
# ─────────────────────────────────────────────────────────────────────────
NN_EXCLUDE_KEYWORDS = (
    # Moda / abbigliamento
    "borsa", "borse", "borsetta", "zaino non", "pochette", "clutch",
    "vestito", "vestiti", "gonna", "pantalone", "pantaloni",
    "camicia", "camicetta", "blazer", "giacca", "cappotto", "cardigan",
    "tuta", "leggings", "calza", "calze", "intimo", "boxer", "mutand",
    "costume da bagno", "bikini",
    # Calzature
    "scarpa", "scarpe", "sneakers", "stivale", "stivali", "stivaletto",
    "sandalo", "sandali", "ciabatte", "infradito", "decollete",
    # Beauty / cura
    "profumo", "profumi", "trucco", "make up", "makeup", "rossetto",
    "mascara", "fondotinta", "ombretto", "smalto", "shampoo",
    # Gioielli moda (non collezionismo nerd)
    "anello", "anelli", "bracciale", "braccialetto", "collana",
    # Bambini / puericultura (a meno che non sia gioco)
    "passeggino", "seggiolino auto", "lettino", "fasciatoio",
    # Casa / arredo
    "cuscino", "tovaglia", "lenzuola", "asciugamano",
)


def _word_match(pattern: str, text: str) -> bool:
    """Match con word-boundary: il pattern e' una parola/locuzione,
    cerchiamo che compaia delimitata da non-parola (\\b).
    Es: 'card' matcha 'card' o 'gift card' ma non 'cardine'.
    Multi-word ('mario kart') funziona perche' lo spazio e' un confine.
    """
    return re.search(rf"\b{re.escape(pattern)}\b", text) is not None


def _matches_nn_keywords(*texts: Optional[str]) -> bool:
    """True se uno dei testi contiene una keyword NerdNostalgia in modo
    word-boundary safe (no substring match)."""
    combined = " ".join(t.lower() for t in texts if t)
    return any(_word_match(kw, combined) for kw in NN_KEYWORDS)


def _has_exclude_keyword(title: Optional[str]) -> bool:
    """True se il titolo contiene una keyword di esclusione (moda, beauty,
    casa, ecc). Controlla SOLO il titolo perche' la description tende ad
    aggiungere troppi falsi positivi (es. 'borsa di plastica per spedizione').
    """
    if not title:
        return False
    t = title.lower()
    return any(_word_match(kw, t) for kw in NN_EXCLUDE_KEYWORDS)


# ─────────────────────────────────────────────────────────────────────────
# Auto-detect categoria/sottocategoria dal titolo (+ descrizione)
# ─────────────────────────────────────────────────────────────────────────
#
# Match in ordine di specificita': prima le sottocategorie carte, poi
# console specifiche, poi sottocategorie nerdate, poi top-level fallback.
# Ogni regola e' (slug_target, tuple di keyword da cercare).
#
# Strategia: il primo match vince. Vince la sottocategoria piu' specifica
# che combacia con qualche keyword del titolo.

CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    # ─── PRIORITA' 1: forma fisica/merchandise → Nerdate/Gadget
    # (vince anche se il franchise e' pokemon/disney/marvel)
    # Esempio: "Quadro pirografato pokemon" → gadget, NON carte/pokemon
    ("gadget", (
        "quadro", "quadretto", "orecchini", "spilla", "spille",
        "portachiavi", "tappetino", "astuccio", "zainetto",
        "fiocco nascita", "sticker", "stickers", "tatuaggi",
        "poster", "campanella", "magnete", "calamita",
        "borraccia", "tazza", "felpa", "maglietta", "t-shirt", "tshirt",
        "cosplay", "cover", "pirografat",
    )),

    # ─── PRIORITA' 2: Funko Pop / Action Figure / Modellini (form fisica)
    ("funko-pop",     ("funko", "bitty pop")),
    ("action-figure", ("action figure", "warhammer", "neca",
                       "mafex", "shf ", "s.h.figuarts")),
    ("modellini",     ("modellino", "modellini", "lego", "playmobil",
                       "miniatura", "miniature", "macchinina",
                       "macchinine", "cars disney")),
    ("peluche",       ("peluche", "plush")),

    # ─── PRIORITA' 3: Videogame disco/cartuccia (console name in titolo)
    # Console+game name → videogiochi/giochi (es. "Spiderman 2 PSP")
    ("giochi", (
        "psp", "ps vita", "psvita", "ps1", "ps2", "ps3", "ps4", "ps5",
        "playstation", "xbox", "gamecube", "wii", "gba", "nds", "3ds",
        "nintendo switch", "nintendo64", "n64", "snes",
        "sega", "dreamcast", "megadrive", "mega drive", "saturn",
        "gameboy", "game boy", "atari",
        "uncharted", "the last of us", "mario kart", "mario party",
        "zelda", "metroid", "kirby", "tetris", "sonic", "doom", "halo",
        "fifa", "pes ", "nba 2k", "minecraft", "fortnite",
        "skyrim", "fallout", "gta ", "call of duty", "battlefield",
        "ducktales", "robocop", "spiderman", "spider-man",
        "invizimals", "prince of persia", "mario kart",
        "mario bros", "super mario", "donkey kong",
    )),

    # ─── PRIORITA' 4: accessori console
    ("accessori", (
        "controller", "joypad", "joystick", "dualshock", "dualsense",
        "pad nintendo", "memory card", "lente ingrandimento",
        "base ricarica ps", "dashcam",
    )),

    # ─── PRIORITA' 5: Carte (franchise specifico nel titolo)
    ("pokemon",             ("pokemon", "pokémon", "pokeball", "pikachu",
                             "charizard", "eevee", "mew", "mewtwo")),
    ("magic-the-gathering", ("magic the gathering", " mtg",)),
    ("yu-gi-oh",            ("yu-gi-oh", "yugioh", "yu gi oh")),
    ("dragon-ball",         ("dragon ball", "dragonball")),
    ("one-piece",           ("one piece",)),
    ("carte",               ("lorcana", "tcg ", "carte da gioco",
                             "trading card", "keyforge",
                             "treasure box", "anthology")),

    # ─── PRIORITA' 6: Gadget franchise (Disney/Marvel/HP senza forma)
    ("gadget", (
        "marvel", "harry potter", "stranger things",
        "studio ghibli", "ghibli", "disney", "topolino",
        "stitch", "groot", "iron man", "spidey",
        "minions", "duracel", "kinder", "sorpresa", "uovo kinder",
        "manga", "fumetto", "fumetti", "lucca comics", "comicon",
        "naruto", "anime", "figurine", "calciatori", "panini",
    )),

    # ─── PRIORITA' 7: Top-level generici
    ("videogiochi", ("videogioco", "videogame", "videogiochi",
                     "nintendo", "console", "gaming")),
    ("carte",       (" carta ", " carte ", " card ")),
    ("nerdate",     ("nerd", "vintage", "retro")),
]


def _detect_category_slug(*texts: Optional[str]) -> Optional[str]:
    """Ritorna lo slug della categoria piu' specifica che matcha. None se
    nessuna regola matcha.

    Usa word-boundary matching cosi' 'card' non matcha 'cardine' e
    'pes ' non sbatte su 'pesante'. Le regole con trailing space dei vecchi
    pattern (es. 'pes ', 'tcg ') vengono normalizzate.
    """
    combined = " ".join(t.lower() for t in texts if t)
    for slug, keywords in CATEGORY_RULES:
        for kw in keywords:
            if _word_match(kw.strip(), combined):
                return slug
    return None


def _resolve_category_id(db: Session, slug: str) -> Optional[int]:
    """Lookup category_id by slug."""
    cat = db.query(Category).filter(Category.slug == slug).first()
    return cat.id if cat else None


def _admin_user_id(db: Session) -> int:
    """Trova l'id dell'admin (owner di default per gli articoli importati)."""
    user = db.query(User).order_by(User.id.asc()).first()
    if not user:
        raise RuntimeError("Nessun utente in DB, impossibile assegnare gli articoli importati")
    return user.id


def _save_photo(photo_bytes: bytes, article_id: int) -> Optional[str]:
    """Salva una foto Vinted come WebP locale (+ thumb). Ritorna l'URL pubblico."""
    try:
        with Image.open(io.BytesIO(photo_bytes)) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode in ("P", "RGBA"):
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")

            uid = uuid.uuid4().hex
            dest_dir = ARTICLES_UPLOADS_DIR / str(article_id)
            dest_dir.mkdir(parents=True, exist_ok=True)
            large_path = dest_dir / f"{uid}.webp"
            thumb_path = dest_dir / f"{uid}.thumb.webp"

            def resize(image: Image.Image, max_width: int) -> bytes:
                if image.width > max_width:
                    ratio = max_width / float(image.width)
                    image = image.resize(
                        (max_width, int(image.height * ratio)),
                        Image.Resampling.LANCZOS,
                    )
                out = io.BytesIO()
                image.save(out, format="WEBP", quality=WEBP_QUALITY, method=6)
                return out.getvalue()

            large_path.write_bytes(resize(img.copy(), LARGE_MAX_WIDTH))
            thumb_path.write_bytes(resize(img.copy(), THUMB_MAX_WIDTH))

            relative = f"articles/{article_id}/{large_path.name}"
            return public_url(relative)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Save photo failed: %s", exc)
        return None


def _item_passes_filter(item: VintedItem) -> bool:
    """Decide se l'item e' pertinente a NerdNostalgia.

    Due gate:
      1) Exclusion list sul titolo: se contiene parole chiaramente non-nerd
         (borsa, scarpe, profumo, ...) → reject. Cattura falsi positivi
         come 'Borsa Valentino' la cui description ha 'card' o 'vintage'.
      2) NN_KEYWORDS in word-boundary su titolo/descrizione/branch.
    """
    if _has_exclude_keyword(item.title):
        return False
    return _matches_nn_keywords(
        item.title, item.description, item.catalog_branch_title,
    )


def _apply_item_to_article(
    db: Session,
    item: VintedItem,
    user_id: int,
) -> tuple[Article, str]:
    """Ritorna (article, op) dove op = 'created' | 'updated' | 'skipped'."""
    existing = (
        db.query(Article)
        .filter(Article.vinted_item_id == item.item_id)
        .first()
    )

    # Auto-detect categoria via keyword nel titolo/descrizione/branch
    target_category_id: Optional[int] = None
    detected_slug = _detect_category_slug(
        item.title, item.description, item.catalog_branch_title,
    )
    if detected_slug:
        target_category_id = _resolve_category_id(db, detected_slug)

    now = datetime.now(_dt.UTC)
    price = Decimal(str(item.price)) if item.price else Decimal("0")

    if existing is not None:
        # Update soft: prezzo + sync time + descrizione/categoria SE prima
        # erano vuote (popola dati mancanti senza sovrascrivere edit admin).
        changed = False
        if existing.vinted_price != price:
            existing.vinted_price = price
            changed = True
        if existing.vinted_url != item.url:
            existing.vinted_url = item.url
            changed = True
        new_status = (
            VintedStatus.SOLD if (item.status or "").lower() == "sold"
            else VintedStatus.LISTED
        )
        if existing.vinted_status != new_status:
            existing.vinted_status = new_status
            changed = True
        if (not existing.description) and item.description:
            existing.description = item.description
            changed = True
        if existing.category_id is None and target_category_id is not None:
            existing.category_id = target_category_id
            changed = True
        existing.vinted_synced_at = now
        if changed:
            db.commit()
            db.refresh(existing)
            return existing, "updated"
        return existing, "skipped"

    # Nuovo articolo: pubblicato direttamente (sync Vinted = catalogo live)
    sold_on_vinted = (item.status or "").lower() == "sold"
    article = Article(
        user_id=user_id,
        title=item.title or f"Vinted #{item.item_id}",
        description=item.description,
        price=price,
        currency=item.currency or "EUR",
        condition=ArticleCondition.USED,
        status=ArticleStatus.SOLD if sold_on_vinted else ArticleStatus.PUBLISHED,
        quantity=1,
        category_id=target_category_id,
        images=[],
        vinted_item_id=item.item_id,
        vinted_url=item.url,
        vinted_price=price,
        vinted_status=VintedStatus.SOLD if sold_on_vinted else VintedStatus.LISTED,
        vinted_synced_at=now,
        purchase_platform="Vinted",
        published_at=now if not sold_on_vinted else None,
        sold_at=now if sold_on_vinted else None,
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    # Scarica le foto (best-effort, limita a 8 per articolo)
    saved_urls: List[str] = []
    for url in (item.photos or [])[:8]:
        try:
            data = download_photo(url)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Download photo failed for %s: %s", url, exc)
            continue
        saved = _save_photo(data, article.id)
        if saved:
            saved_urls.append(saved)

    if saved_urls:
        article.images = saved_urls
        db.commit()
        db.refresh(article)

    # Avviso "nuovo arrivo" agli iscritti (best-effort, dopo le foto cosi'
    # il link nell'email punta a un articolo gia' completo).
    if not sold_on_vinted:
        try:
            from utils.category_alerts import notify_new_article
            notify_new_article(db, article)
        except Exception:  # noqa: BLE001
            LOGGER.exception("Notifica nuovo arrivo fallita per %s", article.id)

    return article, "created"


def persist_items(
    db: Session,
    items: "Iterable[VintedItem]",
    triggered_by: str = "cron",
    update_last_run: bool = True,
) -> VintedSyncLog:
    """Pipeline di sola persistenza: prende un iterable di VintedItem già
    fetchati (da dove vuole il chiamante: server-side Playwright, client
    remoto via POST /api/vinted/import, fixture di test, ecc.) e li
    riversa nel DB applicando filtri, auto-detect categoria e upsert.

    Scrive un record in vinted_sync_logs e lo restituisce.

    triggered_by: "cron" | "manual" | "remote" | qualsiasi tag custom.
    update_last_run: se True aggiorna settings.last_run_at al termine.
    """
    log = VintedSyncLog(
        started_at=datetime.now(_dt.UTC),
        triggered_by=triggered_by,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    fetched = 0
    imported = 0
    updated = 0
    skipped = 0

    try:
        owner_user_id = _admin_user_id(db)
        for item in items:
            fetched += 1
            if not _item_passes_filter(item):
                skipped += 1
                continue
            try:
                _, op = _apply_item_to_article(db, item, owner_user_id)
            except Exception:  # noqa: BLE001
                LOGGER.exception("Errore importando item %s", item.item_id)
                skipped += 1
                continue
            if op == "created":
                imported += 1
            elif op == "updated":
                updated += 1
            else:
                skipped += 1

        if update_last_run:
            settings = db.query(VintedSettings).order_by(VintedSettings.id.asc()).first()
            if settings is not None:
                settings.last_run_at = datetime.now(_dt.UTC)
                db.commit()
    except Exception as exc:  # noqa: BLE001
        log.error_message = f"Errore inatteso: {exc}"
        LOGGER.exception("persist_items inattesa")
    finally:
        log.finished_at = datetime.now(_dt.UTC)
        log.items_fetched = fetched
        log.items_imported = imported
        log.items_updated = updated
        log.items_skipped = skipped
        db.commit()
        db.refresh(log)

    return log


def run_sync(db: Session, triggered_by: str = "cron") -> VintedSyncLog:
    """Esegue la sync server-side (Playwright headless) e ritorna il log.

    Wrapper: fa il fetch via vinted_client + delega la persistenza a
    persist_items(). Se sei su un IP datacenter dove Cloudflare blocca
    Playwright, vedi `scripts/sync_from_local.py` e l'endpoint
    POST /api/vinted/import per la pipeline "fetch da Mac → push al server".

    La sync fa SOLO insert/update. NON cancella articoli che spariscono
    da Vinted (scroll parziale → cancellazioni accidentali). Per rimuovere
    un articolo venduto: /admin/articles → status SOLD.
    """
    settings = db.query(VintedSettings).order_by(VintedSettings.id.asc()).first()
    if settings is None or not settings.enabled:
        log = VintedSyncLog(
            started_at=datetime.now(_dt.UTC),
            finished_at=datetime.now(_dt.UTC),
            triggered_by=triggered_by,
            error_message="Sync Vinted disabilitata o non configurata",
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    try:
        items_iter = list(fetch_user_items(settings.vinted_user_id))
    except VintedClientError as exc:
        log = VintedSyncLog(
            started_at=datetime.now(_dt.UTC),
            finished_at=datetime.now(_dt.UTC),
            triggered_by=triggered_by,
            error_message=f"Client Vinted: {exc}",
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        LOGGER.error("Vinted sync fallita: %s", exc)
        return log

    return persist_items(db, items_iter, triggered_by=triggered_by)
