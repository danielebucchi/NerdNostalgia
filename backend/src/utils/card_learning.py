"""
Lo scanner impara dalle conferme.

Ogni carta confermata e' una risposta giusta: invece di buttarla la si
conserva e la si usa in tre modi.

1. MEMORIA. Lo scan confermato diventa un riferimento della carta. Le
   immagini CardTrader sono foto ufficiali, diverse dagli scan per
   colori, luce e nitidezza; due scan della stessa carta fatti con lo
   stesso scanner si somigliano molto di piu'. La seconda copia di una
   carta gia' vista si riconosce anche se l'OCR non legge niente.

2. CONFUSIONI DELL'OCR. Se l'OCR aveva letto "OPOS-O76" e la carta e'
   OP08-076, la S era un 8 e la O uno 0. Contando le coppie si sa quali
   errori fa davvero il tuo scanner, e le letture alternative partono
   da quelli (anche quelli che le regole fisse non prevedono).

3. SOGLIE. Reverse, prima edizione e condizione si stimano con soglie
   decise a tavolino. Ogni conferma porta la misura dello scan e il
   valore vero: con abbastanza esempi le soglie si ricalcolano sui
   tuoi scan. Finche' gli esempi sono pochi restano quelle di partenza.
"""
import json
import logging
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from models.db import CardReference, CardScan, CardScanStatus, OcrCorrection, PersonalCard

LOGGER = logging.getLogger("card_learning")

# Sotto questa somiglianza fra due scan non si e' sicuri che siano la
# stessa carta (le ristampe con la stessa illustrazione arrivano a 0.9).
SOGLIA_RIFERIMENTO = 0.80
MAX_RIFERIMENTI = 10

# Esempi minimi, per parte, prima di fidarsi di una soglia calcolata.
MIN_ESEMPI = 5
CHIAVE_SOGLIE = "card_scanner_soglie"

ORDINE_CONDIZIONI = ["Near Mint", "Slightly Played", "Moderately Played", "Played", "Poor"]


# ── 1. Memoria ────────────────────────────────────────────────────

def _somiglianza(a: str, b: str) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return 1 - bin(int(a, 16) ^ int(b, 16)).count("1") / (len(a) * 4)


def similar_references(db: Session, game_id: int, scan_hash: Optional[str]) -> Dict[int, float]:
    """Blueprint gia' confermati che somigliano a questo scan → la
    somiglianza migliore per ciascuno. Il confronto e' su tutti i
    riferimenti del gioco: sono le tue carte, migliaia al massimo, e un
    confronto di hash costa niente."""
    if not scan_hash:
        return {}
    migliori: Dict[int, float] = {}
    for bp_id, h in db.query(CardReference.blueprint_id, CardReference.dhash) \
            .filter(CardReference.game_id == game_id):
        sim = _somiglianza(scan_hash, h)
        if sim >= SOGLIA_RIFERIMENTO and sim > migliori.get(bp_id, 0):
            migliori[bp_id] = sim
    return dict(sorted(migliori.items(), key=lambda x: -x[1])[:MAX_RIFERIMENTI])


# ── 2. Confusioni dell'OCR ────────────────────────────────────────

def _alnum(s: Optional[str]) -> str:
    return re.sub(r"[^0-9A-Z]", "", (s or "").upper())


def _coppie(letto: str, vero: str) -> List[Tuple[str, str]]:
    """Caratteri letti male, allineando posizione per posizione. Solo
    stringhe della stessa lunghezza: con un carattere in piu' o in meno
    l'allineamento direbbe cose false."""
    a, b = _alnum(letto), _alnum(vero)
    if a and len(a) != len(b):
        # "47" letto per "047": gli zeri davanti non sono un errore
        a, b = a.lstrip("0") or a, b.lstrip("0") or b
    if not a or len(a) != len(b):
        return []
    return [(x, y) for x, y in zip(a, b) if x != y]


def confusions(db: Session, game_id: Optional[int] = None) -> Dict[str, str]:
    """Carattere letto → cifre/lettere che erano davvero, dalla piu'
    frequente. Es. {"S": "8", "O": "0", "E": "6"}."""
    q = db.query(OcrCorrection.read_text, OcrCorrection.true_text)
    if game_id:
        q = q.filter(OcrCorrection.game_id == game_id)
    conta: Dict[str, Counter] = defaultdict(Counter)
    for letto, vero in q:
        for x, y in _coppie(letto, vero):
            conta[x][y] += 1
    return {x: "".join(y for y, _ in c.most_common()) for x, c in conta.items()}


def _registra_correzioni(db: Session, scan: CardScan, card: PersonalCard, expansion_code: str) -> None:
    letto = scan.ocr or {}
    numero_vero = card.card_number
    for kind, grezzo, vero in (
        ("number", letto.get("raw_number"), numero_vero.split("-")[-1] if numero_vero else None),
        ("set", letto.get("raw_set"), expansion_code),
    ):
        if grezzo and vero and _coppie(grezzo, vero):
            db.add(OcrCorrection(game_id=card.game_id, kind=kind,
                                 read_text=str(grezzo)[:50], true_text=str(vero)[:50]))


# ── 3. Soglie ─────────────────────────────────────────────────────

def _percentile(valori: List[float], q: float) -> float:
    v = sorted(valori)
    i = min(len(v) - 1, max(0, int(round(q * (len(v) - 1)))))
    return v[i]


def soglie_binarie(esempi: List[Tuple[float, bool]]) -> Optional[Dict[str, float]]:
    """Da (misura, valore vero) a due soglie con la zona grigia in mezzo:
    sopra `si` e' si', sotto `no` e' no. Il 10% piu' estremo di ciascun
    gruppo e' trattato come rumore."""
    pos = [m for m, v in esempi if v]
    neg = [m for m, v in esempi if not v]
    if len(pos) < MIN_ESEMPI or len(neg) < MIN_ESEMPI:
        return None
    si, no = _percentile(pos, 0.10), _percentile(neg, 0.90)
    if si <= no:  # gruppi sovrapposti: niente zona grigia, taglio a meta'
        si = no = round((si + no) / 2, 4)
    return {"si": round(si, 4), "no": round(no, 4), "esempi": len(esempi)}


def soglie_usura(esempi: List[Tuple[float, str]]) -> Optional[List[List[Any]]]:
    """Da (usura misurata, condizione vera) ai limiti fra una condizione e
    la successiva. Un limite si calcola solo se ci sono abbastanza esempi
    da entrambe le parti; gli altri restano None (→ quello di partenza)."""
    rango = {c: i for i, c in enumerate(ORDINE_CONDIZIONI)}
    dati = [(u, rango["Near Mint" if c == "Mint" else c]) for u, c in esempi
            if (c == "Mint" or c in rango) and u is not None]
    limiti: List[Optional[float]] = []
    for k in range(len(ORDINE_CONDIZIONI) - 1):
        sotto = [u for u, r in dati if r <= k]
        sopra = [u for u, r in dati if r > k]
        if len(sotto) < MIN_ESEMPI or len(sopra) < MIN_ESEMPI:
            limiti.append(None)
        else:
            limiti.append(round((_percentile(sotto, 0.9) + _percentile(sopra, 0.1)) / 2, 4))
    if not any(limiti):
        return None
    return [[l, ORDINE_CONDIZIONI[k]] for k, l in enumerate(limiti)]


def _esempi(db: Session) -> Dict[str, Any]:
    """Coppie (misura dello scan, valore confermato) dalle conferme. Vale
    solo l'analisi fatta sulla carta che e' stata poi confermata."""
    from utils.card_index import GAME_HINTS

    foil: Dict[str, List] = defaultdict(list)
    timbro: List = []
    usura: List = []
    righe = (
        db.query(CardScan, PersonalCard)
        .join(PersonalCard, PersonalCard.id == CardScan.personal_card_id)
        .filter(CardScan.status == CardScanStatus.CONFIRMED)
    )
    for scan, card in righe:
        f = scan.features or {}
        if f.get("blueprint_id") != card.cardtrader_blueprint_id:
            continue
        gioco = GAME_HINTS.get(card.game_id or 0, "")
        rev = (f.get("reverse") or {}).get("score")
        if rev is not None and (f.get("supports") or {}).get("reverse"):
            foil[gioco].append((rev, bool(card.reverse)))
        prima = (f.get("first_edition") or {}).get("score")
        if prima is not None and gioco == "pokemon":
            timbro.append((prima, bool(card.first_edition)))
        cond = f.get("condition") or {}
        misure = [m for m in (cond.get("wear_front"), cond.get("wear_back")) if m is not None]
        if misure and card.condition:
            usura.append((max(misure), card.condition))
    return {"foil": foil, "timbro": timbro, "usura": usura}


def calibrate(db: Session) -> Dict[str, Any]:
    """Ricalcola le soglie dalle conferme e le salva. Restituisce quelle
    nuove (solo le parti con abbastanza esempi)."""
    from helpers.setting import SettingHelper

    e = _esempi(db)
    soglie: Dict[str, Any] = {"foil": {}, "esempi": {
        "foil": {g: len(v) for g, v in e["foil"].items()},
        "timbro": len(e["timbro"]), "usura": len(e["usura"]),
    }}
    for gioco, esempi in e["foil"].items():
        s = soglie_binarie(esempi)
        if s:
            soglie["foil"][gioco] = s
    t = soglie_binarie(e["timbro"])
    if t:
        soglie["timbro"] = t
    u = soglie_usura(e["usura"])
    if u:
        soglie["usura"] = u
    SettingHelper(db=db).upsert(CHIAVE_SOGLIE, json.dumps(soglie))
    return soglie


def load_thresholds(db: Session) -> Dict[str, Any]:
    from helpers.setting import SettingHelper
    try:
        return json.loads(SettingHelper(db=db).get_value(CHIAVE_SOGLIE) or "{}")
    except (TypeError, ValueError):
        return {}


# ── Alla conferma ─────────────────────────────────────────────────

def learn_from_confirmation(db: Session, scan: CardScan, card: PersonalCard, expansion_code: str) -> None:
    """Tutto quello che una conferma insegna. Best effort: un errore qui
    non deve far fallire la conferma."""
    try:
        if scan.dhash and card.cardtrader_blueprint_id:
            db.add(CardReference(blueprint_id=card.cardtrader_blueprint_id, game_id=card.game_id,
                                 dhash=scan.dhash, scan_id=scan.id))
        _registra_correzioni(db, scan, card, expansion_code)
        db.commit()
        calibrate(db)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        LOGGER.warning("Apprendimento dallo scan %s non riuscito: %s", scan.id, exc)


def status(db: Session) -> Dict[str, Any]:
    soglie = load_thresholds(db)
    return {
        "references": db.query(CardReference).count(),
        "corrections": db.query(OcrCorrection).count(),
        "examples": soglie.get("esempi", {}),
        "calibrated": {
            "reverse": sorted(soglie.get("foil", {}).keys()),
            "first_edition": "timbro" in soglie,
            "condition": "usura" in soglie,
        },
    }
