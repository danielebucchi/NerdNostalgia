"""
Guida prezzi delle carte Pokémon: le pagine pubbliche "quanto vale" di ogni
set e di ogni carta (frontend /prezzi-carte-pokemon), per chi cerca su Google
"charizard set base prezzo".

Una volta a settimana, per ogni espansione Pokémon di CardTrader che ha un
set corrispondente su TCGdex (le espansioni senza, cioe' giapponesi, promo
sparse e prodotti, si saltano): il prezzo piu' basso in vendita e il numero
di offerte di ogni carta (una chiamata per espansione), il nome italiano e
l'immagine ufficiale da TCGdex, data di uscita, serie e logo del set. I
prodotti sigillati (buste, mazzi: niente numero di carta) restano fuori.
Le pagine leggono solo dal database: niente chiamate esterne quando qualcuno
le apre.
"""
import logging
import re
import time
import unicodedata
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models.db import PriceGuideCard, PriceGuideSet
from utils import card_names_it

LOGGER = logging.getLogger("price_guide")

PAUSA = 1.0     # fra un'espansione e l'altra: CardTrader e TCGdex hanno limiti


def slug(testo: str) -> str:
    testo = unicodedata.normalize("NFKD", testo or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", testo).strip("-") or "x"


def _numero(fixed_properties: Optional[dict]) -> Optional[str]:
    numero = str((fixed_properties or {}).get("collector_number") or "").split("/")[0].strip()
    return (numero.lstrip("0") or numero) if numero else None


def _tcgdex(lingua: str, set_id: str) -> dict:
    info = card_names_it._in_cache(f"tcgdex:{lingua}:{set_id}",
                                   lambda: card_names_it._get(f"https://api.tcgdex.net/v2/{lingua}/sets/{set_id}"))
    return info if isinstance(info, dict) else {}


def _prezzi(expansion_id: int) -> Dict[int, tuple]:
    """{blueprint_id: (centesimi minimi, offerte)} da una chiamata sola."""
    from utils import cardtrader_client as ct
    data = ct._request("GET", "/marketplace/products", params={"expansion_id": expansion_id})
    out = {}
    if isinstance(data, dict):
        for chiave, prodotti in data.items():
            valori = [c for c in (ct._price_to_cents(p.get("price")) for p in prodotti or []) if c]
            if valori:
                out[int(chiave)] = (min(valori), len(valori))
    return out


def aggiorna_set(db: Session, espansione: dict, set_id: str) -> int:
    """Una espansione: torna quante carte ha salvato."""
    from utils import cardtrader_client as ct
    en, it = _tcgdex("en", set_id), _tcgdex("it", set_id)
    if not en:
        return 0
    adesso = datetime.utcnow()
    riga = db.get(PriceGuideSet, espansione["id"])
    nome_it = it.get("name")
    if riga is None:
        base = slug(nome_it or espansione["name"])
        usato = db.query(PriceGuideSet).filter(PriceGuideSet.slug == base).first()
        riga = PriceGuideSet(id=espansione["id"], slug=base if usato is None else f"{base}-{espansione['id']}")
        db.add(riga)
    riga.name_en = espansione["name"]
    riga.name_it = nome_it
    riga.tcgdex_id = set_id
    riga.release_date = (en.get("releaseDate") or "")[:10] or None
    riga.card_count = (en.get("cardCount") or {}).get("official")
    riga.serie = (it.get("serie") or {}).get("name") or (en.get("serie") or {}).get("name")
    riga.logo_url = f"{en['logo']}.png" if en.get("logo") else None
    riga.updated_at = adesso

    prezzi = _prezzi(espansione["id"])
    carte_en = {(c.get("localId") or "").lstrip("0") or c.get("localId"): c for c in en.get("cards") or []}
    nomi_it = {(c.get("localId") or "").lstrip("0") or c.get("localId"): c.get("name") for c in it.get("cards") or []}
    esistenti = {c.blueprint_id: c for c in db.query(PriceGuideCard).filter(PriceGuideCard.set_id == riga.id)}
    slug_usati = {c.slug for c in esistenti.values()}
    salvate = 0
    for bp in ct.blueprints_cached(espansione["id"]):
        numero = _numero(bp.get("fixed_properties"))
        if not numero:
            continue                                  # busta, mazzo, box: non e' una carta
        tcg = carte_en.get(numero) or {}
        carta = esistenti.get(bp["id"])
        if carta is None:
            nome = nomi_it.get(numero) or tcg.get("name") or bp.get("name") or ""
            base = slug(f"{numero}-{nome}" + (f"-{bp['version']}" if bp.get("version") else ""))
            proposto = base if base not in slug_usati else f"{base}-{bp['id']}"
            slug_usati.add(proposto)
            carta = PriceGuideCard(set_id=riga.id, blueprint_id=bp["id"], slug=proposto)
            db.add(carta)
        carta.number = numero
        carta.name_en = (tcg.get("name") or bp.get("name") or "")[:200]
        if bp.get("version"):
            carta.name_en = f"{carta.name_en} ({bp['version']})"[:200]
        carta.name_it = nomi_it.get(numero)
        carta.image_url = f"{tcg['image']}/high.webp" if tcg.get("image") else None
        minimo, offerte = prezzi.get(bp["id"], (None, 0))
        carta.min_price_cents = minimo
        carta.offers = offerte
        carta.updated_at = adesso
        salvate += 1
    db.commit()
    return salvate


def aggiorna(db: Session, pausa: float = PAUSA, limite: Optional[int] = None) -> Dict[str, int]:
    """Il giro settimanale su tutte le espansioni Pokémon."""
    from utils import cardtrader_client as ct
    if not ct.is_configured():
        return {"set": 0, "carte": 0}
    espansioni = [e for e in ct.expansions_cached() if e.get("game_id") == card_names_it.POKEMON]
    fatti = carte = errori = 0
    for espansione in espansioni:
        set_id = card_names_it._set_pokemon(espansione.get("name") or "")
        if not set_id:
            continue
        try:
            n = aggiorna_set(db, espansione, set_id)
        except Exception as exc:  # noqa: BLE001 — un set rotto non ferma gli altri
            db.rollback()
            errori += 1
            LOGGER.warning("Guida prezzi: %s non aggiornato (%s)", espansione.get("name"), exc)
            continue
        if n:
            fatti += 1
            carte += n
        if limite and fatti >= limite:
            break
        if pausa:
            time.sleep(pausa)
    LOGGER.info("Guida prezzi: %d set, %d carte, %d errori", fatti, carte, errori)
    return {"set": fatti, "carte": carte, "errori": errori}


def _numero_setting(db: Session, chiave: str, predefinito: float) -> float:
    from helpers.setting import SettingHelper
    try:
        return float((SettingHelper(db=db).get_value(chiave) or "").replace(",", "."))
    except ValueError:
        return predefinito


def regola_offerta(db: Session) -> tuple:
    """(cifra fissa, soglia, percentuale) da Impostazioni."""
    return (_numero_setting(db, "buy_offer_fixed", 0.50), _numero_setting(db, "buy_offer_threshold", 4.0),
            _numero_setting(db, "buy_offer_percent", 60.0))


def offerta(centesimi: Optional[int], regola: tuple) -> Optional[float]:
    """Quanto diamo, al massimo, per una carta che vale `centesimi` sul
    mercato: la cifra fissa fino alla soglia, poi la percentuale,
    arrotondata per difetto ai 10 centesimi."""
    if not centesimi:
        return None
    fissa, soglia, percentuale = regola
    valore = centesimi / 100
    if valore <= soglia:
        return round(fissa, 2)
    return int(valore * percentuale / 100 * 10) / 10


def euro(centesimi: Optional[int]) -> Optional[float]:
    return round(centesimi / 100, 2) if centesimi else None


def disponibili(db: Session, blueprint_ids: List[int]) -> Dict[int, dict]:
    """Le nostre carte in vendita sul sito per quei blueprint: {bp: articolo}."""
    from models.db import Article, ArticleStatus, PersonalCard
    if not blueprint_ids:
        return {}
    righe = (db.query(PersonalCard.cardtrader_blueprint_id, Article)
             .join(Article, Article.id == PersonalCard.article_id)
             .filter(PersonalCard.cardtrader_blueprint_id.in_(blueprint_ids),
                     Article.status == ArticleStatus.PUBLISHED, Article.reserved_order_id.is_(None),
                     Article.quantity > 0)
             .all())
    out: Dict[int, dict] = {}
    for bp, a in righe:
        if bp not in out or float(a.price) < out[bp]["price"]:
            out[bp] = {"id": a.id, "title": a.title, "price": float(a.price),
                       "image": (a.images or [None])[0]}
    return out
