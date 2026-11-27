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
# Cambia quando cambia il modo di costruire i dati (nomi, indirizzi): al
# riavvio il server rifa' la guida senza aspettare la domenica.
VERSIONE = "5"
CHIAVE_VERSIONE = "price_guide_version"


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


# Le condizioni, dalla migliore alla peggiore, con la sigla usata nel sito.
CONDIZIONI = [("NM", ("Mint", "Near Mint")), ("SP", ("Slightly Played",)), ("MP", ("Moderately Played",)),
              ("PL", ("Played",)), ("PO", ("Poor",))]
LINGUE = ("it", "en")


# Le versioni della stessa carta, che sul mercato valgono cifre diverse.
VERSIONI = ("normale", "1ed", "reverse")


def _versione(h: dict) -> str:
    if h.get("pokemon_reverse"):
        return "reverse"
    if h.get("first_edition"):
        return "1ed"
    return "normale"


def tabella_prezzi(prodotti: List[dict]) -> Dict[str, Dict[str, Dict[str, int]]]:
    """Il prezzo piu' basso per versione (normale, prima edizione, reverse),
    lingua (italiana, inglese) e condizione: {"normale": {"it": {"NM": 55128}}}.
    Fuori le copie gradate, firmate o alterate. Una condizione peggiore non
    puo' costare piu' di una migliore: se succede (un'offerta alta isolata)
    vale il prezzo della migliore."""
    from utils import cardtrader_client as ct
    sigla = {nome: s for s, nomi in CONDIZIONI for nome in nomi}
    grezzi: Dict[str, Dict[str, Dict[str, int]]] = {}
    for p in prodotti or []:
        h = p.get("properties_hash") or {}
        if p.get("graded") or h.get("signed") or h.get("altered"):
            continue
        lingua, cond = h.get("pokemon_language"), sigla.get(h.get("condition"))
        cent = ct._price_to_cents(p.get("price"))
        if lingua in LINGUE and cond and cent:
            righe = grezzi.setdefault(_versione(h), {}).setdefault(lingua, {})
            righe[cond] = min(cent, righe.get(cond, cent))
    tabella: Dict[str, Dict[str, Dict[str, int]]] = {}
    for versione in VERSIONI:
        for lingua, valori in (grezzi.get(versione) or {}).items():
            tetto, righe = None, {}
            for s, _ in CONDIZIONI:
                if s in valori:
                    righe[s] = valori[s] if tetto is None else min(valori[s], tetto)
                    tetto = righe[s]
            if righe:
                tabella.setdefault(versione, {})[lingua] = righe
    return tabella


def per_versione(prezzi: Optional[dict]) -> Dict[str, Dict[str, Dict[str, int]]]:
    """La tabella salvata, anche nel formato di prima (senza versioni)."""
    if not prezzi:
        return {}
    if any(k in LINGUE for k in prezzi):
        return {"normale": prezzi}
    return prezzi


def prezzo_in_evidenza(tabella: Dict[str, Dict[str, Dict[str, int]]]) -> Optional[int]:
    """Il prezzo da mostrare in griglia: la versione normale (se c'e'), Near
    Mint, italiana se no inglese, se no la condizione migliore che c'e'."""
    tabella = per_versione(tabella)
    for versione in VERSIONI:
        lingue = tabella.get(versione) or {}
        for lingua in LINGUE:
            if (lingue.get(lingua) or {}).get("NM"):
                return lingue[lingua]["NM"]
        for s, _ in CONDIZIONI:
            for lingua in LINGUE:
                if (lingue.get(lingua) or {}).get(s):
                    return lingue[lingua][s]
    return None


def _prezzi(expansion_id: int) -> Dict[int, tuple]:
    """{blueprint_id: (tabella per lingua e condizione, offerte)} da una chiamata sola."""
    from utils import cardtrader_client as ct
    data = ct._request("GET", "/marketplace/products", params={"expansion_id": expansion_id})
    out = {}
    if isinstance(data, dict):
        for chiave, prodotti in data.items():
            if prodotti:
                out[int(chiave)] = (tabella_prezzi(prodotti), len(prodotti))
    return out


def _variante(versione: Optional[str]) -> Optional[str]:
    """"Brown Prerelease | Starlight Holo | 001/062" → "Brown Prerelease": la
    prima parte dice di che variante si tratta, il resto e' rarita' e numero."""
    for parte in (versione or "").split("|"):
        parte = parte.strip()
        if parte and not re.fullmatch(r"[\d/ ]+", parte):
            return parte[:80]
    return None


def _immagine_cardtrader(bp: dict) -> Optional[str]:
    """L'immagine di CardTrader, quando TCGdex non ce l'ha."""
    url = (((bp.get("image") or {}).get("show") or {}).get("url")) or bp.get("image_url")
    if not url:
        return None
    return url if url.startswith("http") else f"https://www.cardtrader.com{url}"


def aggiorna_set(db: Session, espansione: dict, set_id: str) -> int:
    """Una espansione: torna quante carte ha salvato."""
    from utils import cardtrader_client as ct
    en, it = _tcgdex("en", set_id), _tcgdex("it", set_id)
    if not en:
        return 0
    adesso = datetime.utcnow()
    blueprint = [bp for bp in ct.blueprints_cached(espansione["id"]) if _numero(bp.get("fixed_properties"))]
    carte_en = {(c.get("localId") or "").lstrip("0") or c.get("localId"): c for c in en.get("cards") or []}
    # Il set TCGdex e' quello giusto solo se le carte tornano per numero:
    # "Miscellaneous Promos" di CardTrader (promo sparse) ha lo stesso nome di
    # un set TCGdex di una carta sola. Se no, di TCGdex non si usa niente.
    trovate = sum(1 for bp in blueprint if _numero(bp["fixed_properties"]) in carte_en)
    if blueprint and trovate < len(blueprint) / 2:
        en, it, carte_en = {}, {}, {}
    riga = db.get(PriceGuideSet, espansione["id"])
    nome_it = it.get("name")
    if riga is None:
        base = slug(nome_it or espansione["name"])
        usato = db.query(PriceGuideSet).filter(PriceGuideSet.slug == base).first()
        riga = PriceGuideSet(id=espansione["id"], slug=base if usato is None else f"{base}-{espansione['id']}")
        db.add(riga)
    riga.name_en = espansione["name"]
    riga.name_it = nome_it
    riga.tcgdex_id = set_id if en else None
    riga.release_date = (en.get("releaseDate") or "")[:10] or None
    riga.card_count = (en.get("cardCount") or {}).get("official")
    riga.serie = (it.get("serie") or {}).get("name") or (en.get("serie") or {}).get("name")
    riga.logo_url = f"{en['logo']}.png" if en.get("logo") else None
    riga.updated_at = adesso

    prezzi = _prezzi(espansione["id"])
    nomi_it = {(c.get("localId") or "").lstrip("0") or c.get("localId"): c.get("name") for c in it.get("cards") or []}
    esistenti = {c.blueprint_id: c for c in db.query(PriceGuideCard).filter(PriceGuideCard.set_id == riga.id)}
    # Per i Pokémon CardTrader mette nella "versione" rarita' e numero
    # ("Holo Rare | 4/102"): conta solo se due carte del set hanno lo stesso
    # numero (varianti vere), e allora distingue nome e indirizzo.
    per_numero: Dict[str, int] = {}
    for bp in blueprint:
        per_numero[_numero(bp["fixed_properties"])] = per_numero.get(_numero(bp["fixed_properties"]), 0) + 1
    # Gli indirizzi si ricalcolano ogni volta: prima nomi provvisori, cosi'
    # lo scambio di due indirizzi non urta il vincolo di unicita'.
    for c in esistenti.values():
        c.slug = f"tmp-{c.blueprint_id}"
    db.flush()
    slug_usati: set = set()
    salvate = 0
    for bp in sorted(blueprint, key=lambda b: b["id"]):
        numero = _numero(bp.get("fixed_properties"))
        tcg = carte_en.get(numero) or {}
        variante = _variante(bp.get("version")) if per_numero[numero] > 1 else None
        nome = nomi_it.get(numero) or tcg.get("name") or bp.get("name") or ""
        base = slug(f"{numero}-{nome}" + (f"-{variante}" if variante else ""))
        proposto = base if base not in slug_usati else f"{base}-{bp['id']}"
        slug_usati.add(proposto)
        carta = esistenti.get(bp["id"])
        if carta is None:
            carta = PriceGuideCard(set_id=riga.id, blueprint_id=bp["id"])
            db.add(carta)
        carta.slug = proposto
        carta.number = numero
        carta.name_en = (tcg.get("name") or bp.get("name") or "")[:200]
        if variante:
            carta.name_en = f"{carta.name_en} ({variante})"[:200]
        carta.name_it = nomi_it.get(numero)
        carta.image_url = f"{tcg['image']}/high.webp" if tcg.get("image") else _immagine_cardtrader(bp)
        tabella, offerte = prezzi.get(bp["id"], ({}, 0))
        carta.prices = tabella or None
        carta.min_price_cents = prezzo_in_evidenza(tabella)
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
    if fatti:
        from helpers.setting import SettingHelper
        SettingHelper(db=db).upsert(CHIAVE_VERSIONE, VERSIONE)
    LOGGER.warning("Guida prezzi: %d set, %d carte, %d errori", fatti, carte, errori)
    return {"set": fatti, "carte": carte, "errori": errori}


def _numero_setting(db: Session, chiave: str, predefinito: float) -> float:
    from helpers.setting import SettingHelper
    try:
        return float((SettingHelper(db=db).get_value(chiave) or "").replace(",", "."))
    except ValueError:
        return predefinito


def regola_offerta(db: Session) -> dict:
    """La regola di "Valuta la tua carta", da Impostazioni."""
    return {"fissa": _numero_setting(db, "buy_offer_fixed", 0.50),
            "soglia": _numero_setting(db, "buy_offer_threshold", 4.0),
            "percentuale": _numero_setting(db, "buy_offer_percent", 60.0),
            "kg": {"vintage": _numero_setting(db, "buy_bulk_vintage", 7.0),
                   "medio": _numero_setting(db, "buy_bulk_medio", 5.0),
                   "modern": _numero_setting(db, "buy_bulk_modern", 3.0)}}


# Le epoche delle carte a peso, dalla data di uscita del set: il bordo giallo
# arriva con Rubino e Zaffiro (luglio 2003, prima Wizards of the Coast ed
# e-Card), quello argentato con Scarlatto e Violetto (31 marzo 2023).
INIZIO_MEDIO = "2003-06-01"
INIZIO_MODERN = "2023-03-31"
NOMI_EPOCA = {"vintage": "vintage", "medio": "bordo giallo", "modern": "modern"}


def epoca(data_uscita: Optional[str]) -> str:
    if data_uscita and data_uscita < INIZIO_MEDIO:
        return "vintage"
    if data_uscita and data_uscita < INIZIO_MODERN:
        return "medio"
    return "modern"


def energia(nome: str) -> bool:
    """Le carte Energia si chiamano "... Energy" ("Fire Energy", "Double
    Colorless Energy"); "Super Energy Removal" o "Energy Search" sono
    Allenatori. Il nome e' quello inglese, senza la variante tra parentesi."""
    nome = re.sub(r"\(.*?\)", "", nome or "").strip()
    return bool(re.search(r"\benergy$", nome, re.IGNORECASE))


def offerta(centesimi: Optional[int], regola: dict, data_uscita: Optional[str] = None,
            nome: str = "") -> dict:
    """Quanto diamo, al massimo, per una carta che vale `centesimi` sul
    mercato. Sotto la cifra fissa (0,50 €) non si compra singola: va a
    peso, al prezzo della sua epoca (le energie a peso no). Fino alla
    soglia la cifra fissa, oltre la percentuale arrotondata per difetto ai
    10 centesimi. Torna {"tipo": "singola", "euro": ...},
    {"tipo": "peso", "epoca": ..., "euro_kg": ...}, {"tipo": "no"} o {}."""
    if not centesimi:
        return {}
    valore = centesimi / 100
    if valore < regola["fissa"]:
        if energia(nome):
            return {"tipo": "no"}
        e = epoca(data_uscita)
        return {"tipo": "peso", "epoca": NOMI_EPOCA[e], "euro_kg": regola["kg"][e]}
    if valore <= regola["soglia"]:
        return {"tipo": "singola", "euro": round(regola["fissa"], 2)}
    return {"tipo": "singola", "euro": int(valore * regola["percentuale"] / 100 * 10) / 10}


def da_rifare(db: Session) -> bool:
    """Vuota, o costruita da una versione precedente del codice."""
    from helpers.setting import SettingHelper
    vuota = db.query(PriceGuideCard.id).first() is None
    return vuota or SettingHelper(db=db).get_value(CHIAVE_VERSIONE, default="") != VERSIONE


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
