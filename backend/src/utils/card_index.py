"""
Indice locale dei blueprint CardTrader e abbinamento scan → carta.

L'abbinamento mette insieme tre indizi, nessuno sufficiente da solo:

- il NUMERO letto (forte, ma l'OCR su caratteri piccoli sbaglia una cifra
  ogni tanto, e lo stesso numero esiste in centinaia di espansioni);
- la SIGLA del set, quando e' stampata (Pokemon recenti, Magic,
  Yu-Gi-Oh!, One Piece) e validata contro le sigle che esistono davvero;
- l'IMMAGINE: il simbolo dell'espansione e l'illustrazione distinguono
  le ristampe che hanno lo stesso nome e lo stesso numero. Si confronta
  lo scan con l'immagine CardTrader via dHash, che regge bene la
  differenza fra uno scan e una foto ufficiale (stessa carta = stessi
  gradienti, anche se i colori non coincidono).

Il nome letto in alto entra come conferma e come rete di salvataggio:
se il numero e' letto male, la carta giusta arriva lo stesso fra i
candidati perche' ha il nome giusto.

Il risultato sono CANDIDATI ordinati, non una risposta: si conferma a
mano, e la confidenza dice quanto guardare con attenzione.
"""
import difflib
import io
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import requests
from PIL import Image, ImageOps
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from models.db import CardBlueprint
from utils import cardtrader_client as ct
from utils.card_ocr import LetturaCarta
from utils.cardtrader_sync import _norm_number

LOGGER = logging.getLogger("card_index")

IMAGE_BASE = "https://www.cardtrader.com"
DHASH_SIZE = 16  # 16x16 = 256 bit
# Quanti candidati confrontare per immagine: ogni confronto nuovo costa
# il download di un'anteprima (poi resta in cache nell'indice). Con
# l'indice intero un nome come Charizard ha decine di versioni: il
# confronto le deve vedere quasi tutte.
MAX_CONFRONTI_IMMAGINE = 60
# ...e se in testa c'e' un gruppo di pari merito piu' grande, lo si
# confronta tutto fino a questo tetto: tagliare a caso fra pari merito
# vuol dire escludere a caso la carta giusta.
MAX_CONFRONTI_PARI = 150
DOWNLOAD_PARALLELI = 8
MAX_CANDIDATI = 6

# game_id CardTrader → formato dei codici stampati (vedi card_ocr)
GAME_HINTS = {1: "magic", 4: "yugioh", 5: "pokemon", 15: "onepiece"}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── dHash ─────────────────────────────────────────────────────────

def dhash(img: Image.Image, size: int = DHASH_SIZE) -> str:
    """Hash per differenza: per ogni riga, se un pixel e' piu' chiaro del
    successivo. Bastano Pillow e niente numpy."""
    g = ImageOps.autocontrast(img.convert("L")).resize((size + 1, size), Image.LANCZOS)
    px = g.tobytes()  # modo L: un byte per pixel
    bits = 0
    for r in range(size):
        riga = px[r * (size + 1):(r + 1) * (size + 1)]
        for c in range(size):
            bits = (bits << 1) | (1 if riga[c] > riga[c + 1] else 0)
    return f"{bits:0{size * size // 4}x}"


def similarity(a: str, b: str) -> float:
    """1.0 = identiche, ~0.5 = immagini qualsiasi."""
    if not a or not b or len(a) != len(b):
        return 0.0
    diff = bin(int(a, 16) ^ int(b, 16)).count("1")
    return 1 - diff / (len(a) * 4)


def _anteprima(url: str) -> str:
    """CardTrader ha l'immagine in piu' formati: per un hash 16x16 basta la
    piu' piccola, che pesa un decimo."""
    return url.replace("/show_", "/preview_")


def _scarica_dhash(url: str) -> Optional[str]:
    try:
        resp = requests.get(_anteprima(url), timeout=15)
        resp.raise_for_status()
        with Image.open(io.BytesIO(resp.content)) as im:
            return dhash(im.convert("RGB"))
    except Exception as exc:  # noqa: BLE001
        LOGGER.info("Immagine %s non scaricata: %s", url, exc)
        return None


def _dhash_blueprints(db: Session, bps: List[CardBlueprint]) -> Dict[int, str]:
    """Hash dei blueprint, scaricando in parallelo quelli che mancano. La
    sessione DB resta in questo thread: nei worker solo rete e Pillow."""
    mancanti = [bp for bp in bps if not bp.dhash and bp.image_url]
    if mancanti:
        with ThreadPoolExecutor(max_workers=DOWNLOAD_PARALLELI) as pool:
            for bp, h in zip(mancanti, pool.map(lambda b: _scarica_dhash(b.image_url), mancanti)):
                if h:
                    bp.dhash = h
        db.commit()
    return {bp.id: bp.dhash for bp in bps if bp.dhash}


# ── Indice ────────────────────────────────────────────────────────

def _image_url(bp: dict) -> Optional[str]:
    img = bp.get("image") or {}
    path = ((img.get("show") or {}).get("url")) or img.get("url")
    if path:
        return path if path.startswith("http") else IMAGE_BASE + path
    return bp.get("image_url")


def index_expansion(db: Session, exp: dict) -> int:
    """Mette nell'indice le carte singole di un'espansione. Buste, box e
    gadget non hanno numero di collezione: fuori."""
    bps = ct.blueprints_cached(exp["id"])
    esistenti = {
        r[0]: r[1] for r in
        db.query(CardBlueprint.id, CardBlueprint.dhash)
        .filter(CardBlueprint.expansion_id == exp["id"]).all()
    }
    n = 0
    for bp in bps:
        numero = (bp.get("fixed_properties") or {}).get("collector_number")
        if not numero:
            continue
        riga = CardBlueprint(
            id=bp["id"],
            game_id=bp.get("game_id") or exp.get("game_id"),
            expansion_id=exp["id"],
            expansion_code=(exp.get("code") or "").lower(),
            expansion_name=exp.get("name"),
            name=bp.get("name") or "",
            version=bp.get("version"),
            collector_number=str(numero),
            number_norm=_norm_number(numero),
            image_url=_image_url(bp),
            # L'hash vale finche' l'immagine non cambia: lo si conserva.
            dhash=esistenti.get(bp["id"]),
            editable=_editable(bp),
            indexed_at=_now(),
        )
        db.merge(riga)
        n += 1
    db.commit()
    return n


def _editable(bp: dict) -> str:
    """"first_edition,pokemon_language:en|it|fr,pokemon_reverse". Per la
    lingua anche i valori: dicono in che lingue la carta esiste."""
    parti = []
    for e in bp.get("editable_properties") or []:
        nome = e.get("name")
        if not nome or nome in ("condition", "signed", "altered"):
            continue
        if nome.endswith("_language"):
            nome += ":" + "|".join(str(v) for v in e.get("possible_values") or [])
        parti.append(nome)
    return ",".join(sorted(parti))


def lingue(editable: Optional[str]) -> Optional[set]:
    """Lingue in cui la carta esiste. Insieme vuoto = CardTrader non
    prevede la scelta della lingua (set solo giapponesi, di solito)."""
    if editable is None:
        return None
    for p in editable.split(","):
        if p.split(":")[0].endswith("_language"):
            return set(p.split(":", 1)[1].split("|")) if ":" in p else None
    return set()


def editable_for(db: Session, bp: CardBlueprint) -> str:
    """Attributi CardTrader della carta. Le righe indicizzate prima che
    l'indice li ricordasse li recuperano qui, una volta sola."""
    # Righe vecchie: senza attributi, o con la lingua senza i valori.
    vecchia = bp.editable is not None and "_language" in bp.editable and ":" not in bp.editable
    if bp.editable is None or vecchia:
        for raw in ct.blueprints_cached(bp.expansion_id):
            if raw.get("id") == bp.id:
                bp.editable = _editable(raw)
                break
        else:
            bp.editable = ""
        db.commit()
    return bp.editable


def indexed_expansions(db: Session, game_id: int) -> set:
    return {
        r[0] for r in db.query(CardBlueprint.expansion_id)
        .filter(CardBlueprint.game_id == game_id).distinct()
    }


# Avanzamento della costruzione indice, per gioco. In memoria: se il
# processo riparte, si rilancia e riprende da dove era (le espansioni gia'
# indicizzate si saltano).
_BUILD: Dict[int, Dict[str, Any]] = {}
_BUILD_LOCK = threading.Lock()


def build_status(db: Session) -> List[Dict[str, Any]]:
    righe = (
        db.query(CardBlueprint.game_id, func.count(CardBlueprint.id),
                 func.count(func.distinct(CardBlueprint.expansion_id)),
                 func.max(CardBlueprint.indexed_at))
        .group_by(CardBlueprint.game_id).all()
    )
    out = {
        g: {"game_id": g, "blueprints": n, "expansions": e,
            "updated_at": u.isoformat() if u else None}
        for g, n, e, u in righe
    }
    for g, st in _BUILD.items():
        out.setdefault(g, {"game_id": g, "blueprints": 0, "expansions": 0, "updated_at": None})
        out[g]["build"] = dict(st)
    return list(out.values())


def start_build(game_id: int, session_factory, full: bool = False) -> bool:
    """Indicizza tutte le espansioni di un gioco in un thread. Ritorna
    False se una costruzione per quel gioco e' gia' in corso."""
    with _BUILD_LOCK:
        if _BUILD.get(game_id, {}).get("running"):
            return False
        _BUILD[game_id] = {"running": True, "done": 0, "total": 0, "errors": 0,
                           "started_at": _now().isoformat()}

    def _run():
        db = session_factory()
        st = _BUILD[game_id]
        try:
            exps = [e for e in ct.expansions_cached() if e.get("game_id") == game_id]
            fatte = set() if full else indexed_expansions(db, game_id)
            todo = [e for e in exps if e["id"] not in fatte]
            st["total"] = len(todo)
            for e in todo:
                try:
                    index_expansion(db, e)
                except Exception as exc:  # noqa: BLE001
                    db.rollback()
                    st["errors"] += 1
                    LOGGER.warning("Espansione %s non indicizzata: %s", e.get("id"), exc)
                st["done"] += 1
                # CardTrader limita le richieste: un export ogni ~0.2s
                # tiene l'indice completo di un gioco sotto i 5 minuti.
                time.sleep(0.2)
        except Exception as exc:  # noqa: BLE001
            st["error"] = str(exc)
            LOGGER.exception("Indice gioco %s fallito", game_id)
        finally:
            st["running"] = False
            st["finished_at"] = _now().isoformat()
            db.close()

    threading.Thread(target=_run, name=f"card-index-{game_id}", daemon=True).start()
    return True


# ── Abbinamento ───────────────────────────────────────────────────

_PAROLE = re.compile(r"[a-zà-ÿ0-9]+")


def _tokens(s: Optional[str]) -> List[str]:
    return _PAROLE.findall((s or "").lower())


# "Si evolve da Charmeleon" nomina un'altra carta: fuori dal confronto,
# se no Charmeleon vale quanto Charizard.
_EVOLUZIONE = re.compile(
    r"(evolves\s+from|si\s+evolve\s+da|[eé]volution\s+de|entwickelt\s+sich\s+aus|evoluciona\s+de)\s+\S+",
    re.I,
)


def _senza_evoluzione(testo: str) -> str:
    return _EVOLUZIONE.sub(" ", testo or "")


# Nel nome CardTrader ma quasi mai letto dall'OCR: il livello ("Lv.44"),
# scritto minuscolo accanto al nome. Pesarlo dimezzerebbe il punteggio
# della carta giusta ("Crobat G Lv.44") rispetto ai Crobat semplici.
PAROLE_DI_SERVIZIO = {"lv"}


def _name_score(name: str, testo: str) -> float:
    """Quanto del nome del blueprint compare nel testo letto, 0..1.
    Per parola e con tolleranza (Tesseract legge "Charizah" per
    "Charizard"): una parola conta se somiglia almeno all'80% a una letta."""
    # Anche le sigle corte contano (ex, GX, V): "Charizard VMAX" non e'
    # "Charizard". I numeri no, sono quasi sempre HP o danni.
    parole = [p for p in _tokens(name) if not p.isdigit() and (len(p) >= 2 or p == "v")
              and p not in PAROLE_DI_SERVIZIO]
    if not parole:
        return 0.0
    lette = set(_tokens(testo))
    if not lette:
        return 0.0
    trovate = 0.0
    for p in parole:
        if p in lette:
            trovate += 1
            continue
        m = difflib.get_close_matches(p, lette, n=1, cutoff=0.8)
        if m:
            trovate += 0.8
    return trovate / len(parole)


# Errori OCR tipici sulle sigle: per ogni carattere, cosa puo' essere
# stato in realta' (la D di DMU letta O e' il piu' frequente).
_SCAMBI = {
    "0": "0O", "O": "O0D", "D": "DO", "1": "1I", "I": "I1L", "L": "LI",
    "5": "5S", "S": "S5", "8": "8B", "B": "B8",
}


def _varianti_sigla(sigla: str, appreso: Optional[dict] = None) -> List[str]:
    """Tutte le letture alternative. Le sigle sono di 2-5 caratteri: le
    combinazioni restano poche centinaia al massimo. Le confusioni
    imparate dalle correzioni si aggiungono a quelle fisse."""
    out = [""]
    for ch in sigla[:5]:
        scelte = _SCAMBI.get(ch, ch)
        scelte += "".join(c for c in (appreso or {}).get(ch, "") if c not in scelte)
        out = [o + alt for o in out for alt in scelte]
    return out


def resolve_set_codes(game_id: int, sigle: Iterable[str], tutte: bool = False,
                      appreso: Optional[dict] = None) -> List[dict]:
    """Sigle lette → espansioni CardTrader che esistono davvero."""
    exps = [e for e in ct.expansions_cached() if e.get("game_id") == game_id]
    per_codice: Dict[str, List[dict]] = {}
    for e in exps:
        per_codice.setdefault((e.get("code") or "").lower(), []).append(e)
    trovate: List[dict] = []
    for sigla in sigle:
        for v in _varianti_sigla(sigla.upper(), appreso):
            for e in per_codice.get(v.lower(), []):
                if e not in trovate:
                    trovate.append(e)
        if trovate and not tutte:
            break  # la prima sigla valida basta; le altre sono rumore
    return trovate


def _numero_compatibile(norm_candidato: str, norm_letto: str) -> int:
    """2 = stesso numero, 1 = stesso numero con suffisso di variante
    ("op01064b" per "op01064": arte alternativa), 0 = diverso."""
    if not norm_letto:
        return 0
    if norm_candidato == norm_letto:
        return 2
    if norm_candidato.startswith(norm_letto) and norm_candidato[len(norm_letto):].isalpha() \
            and len(norm_candidato) - len(norm_letto) <= 2:
        return 1
    return 0


def _numeri(lettura: LetturaCarta) -> List[str]:
    """Il numero letto e le sue letture alternative, normalizzati."""
    out = []
    for n in [lettura.number, *(lettura.alt_numbers or [])]:
        norm = _norm_number(n)
        if norm and norm not in out:
            out.append(norm)
    return out


def _pool(
    db: Session, game_id: int, lettura: LetturaCarta,
    expansion_ids: Optional[List[int]],
) -> List[CardBlueprint]:
    """Candidati grezzi: per numero e per nome, uniti."""
    base = db.query(CardBlueprint).filter(CardBlueprint.game_id == game_id)
    if expansion_ids:
        base = base.filter(CardBlueprint.expansion_id.in_(expansion_ids))
    pool: Dict[int, CardBlueprint] = {}

    for norm in _numeri(lettura):
        for bp in base.filter(CardBlueprint.number_norm.like(f"{norm}%")).limit(3000):
            if _numero_compatibile(bp.number_norm or "", norm):
                pool[bp.id] = bp

    # Per nome: le parole lunghe della fascia alta. Quelle corte sono
    # quasi sempre rumore (HP, PS, simboli letti come lettere).
    parole = sorted({p for p in _tokens(lettura.name_text) if len(p) >= 4 and p.isalpha()},
                    key=len, reverse=True)[:4]
    if parole:
        filtro = or_(*[CardBlueprint.name.ilike(f"%{p}%") for p in parole])
        for bp in base.filter(filtro).limit(1500):
            pool.setdefault(bp.id, bp)

    if not pool and expansion_ids:
        # Espansione nota ma ne' numero ne' nome letti: tutta l'espansione,
        # deciderà l'immagine.
        for bp in base.limit(600):
            pool[bp.id] = bp
    return list(pool.values())


def match(
    db: Session,
    game_id: int,
    lettura: LetturaCarta,
    scan_hash: Optional[str],
    expansion_id: Optional[int] = None,
    appreso: Optional[dict] = None,
) -> Dict[str, Any]:
    """Candidati ordinati per lo scan. Ritorna {candidates, confidence,
    expansions_from_code}."""
    # Sigla → espansioni vere (e se non sono ancora nell'indice, le si
    # indicizza adesso: e' un export solo, non il gioco intero).
    da_sigla: List[dict] = []
    if not expansion_id and lettura.set_codes:
        try:
            # Con piu' letture dello stesso codice (OP05/OP08) valgono
            # tutte: decide l'immagine.
            da_sigla = resolve_set_codes(game_id, lettura.set_codes, tutte=bool(lettura.alt_numbers),
                                         appreso=appreso)
        except ct.CardTraderError as exc:
            LOGGER.info("Sigle non risolte: %s", exc)
    nell_indice = indexed_expansions(db, game_id)
    for e in da_sigla + ([{"id": expansion_id, "game_id": game_id}] if expansion_id else []):
        if e["id"] not in nell_indice:
            if "code" not in e:
                e = next((x for x in ct.expansions_cached() if x["id"] == e["id"]), e)
            index_expansion(db, e)

    exp_ids = [expansion_id] if expansion_id else None
    pool = _pool(db, game_id, lettura, exp_ids)
    # Con la sigla letta si preferiscono le sue espansioni, ma senza
    # escludere le altre: una sigla letta male non deve nascondere la
    # carta giusta.
    sigla_ids = {e["id"] for e in da_sigla}
    if sigla_ids and not exp_ids:
        pool += [bp for bp in _pool(db, game_id, lettura, list(sigla_ids)) if bp not in pool]

    # Memoria: le carte gia' confermate con uno scan che somiglia a questo
    # entrano fra i candidati anche se OCR e nome non le trovano.
    from utils.card_learning import similar_references
    gia_viste = similar_references(db, game_id, scan_hash) if scan_hash else {}
    if gia_viste and not exp_ids:
        presenti = {bp.id for bp in pool}
        pool += db.query(CardBlueprint).filter(
            CardBlueprint.id.in_([i for i in gia_viste if i not in presenti])).all()

    numeri = _numeri(lettura)
    totale = _norm_number(lettura.total)
    # Espansioni del pool in cui esiste una carta col numero del totale
    # stampato ("/165" → c'e' una 165): indizio debole ma utile coi
    # Pokemon vecchi, che non hanno altro.
    con_totale = set()
    if totale:
        ids = {bp.expansion_id for bp in pool}
        if ids:
            con_totale = {
                r[0] for r in db.query(CardBlueprint.expansion_id)
                .filter(CardBlueprint.expansion_id.in_(ids), CardBlueprint.number_norm == totale)
                .distinct()
            }

    testo_nome = _senza_evoluzione(f"{lettura.name_text}\n{lettura.full_text}")
    nomi = {bp.id: _name_score(bp.name, testo_nome) for bp in pool}
    # Se il nome si e' letto, una carta che col nome non c'entra niente e'
    # li' solo per il numero — e il numero puo' essere letto male.
    nome_letto = max(nomi.values(), default=0) >= 0.8
    punteggi = []
    for bp in pool:
        s = 0.0
        num = max((_numero_compatibile(bp.number_norm or "", n) for n in numeri), default=0)
        s += {2: 10, 1: 8, 0: 0}[num]
        if bp.expansion_id in sigla_ids:
            s += 8
        if bp.expansion_id in con_totale:
            s += 3
        s += 12 * nomi[bp.id]
        if nome_letto and nomi[bp.id] == 0:
            s -= 6
        punteggi.append([s, bp, num, None])
    punteggi.sort(key=lambda x: -x[0])

    # L'immagine decide fra quelli rimasti in testa.
    if scan_hash:
        soglia = punteggi[0][0] - 4 if punteggi else 0
        pari = sum(1 for r in punteggi if r[0] >= soglia)
        testa = punteggi[:min(max(MAX_CONFRONTI_IMMAGINE, pari), MAX_CONFRONTI_PARI)]
        hash_bp = _dhash_blueprints(db, [r[1] for r in testa])
        for riga in testa:
            h = hash_bp.get(riga[1].id)
            if h:
                sim = similarity(scan_hash, h)
                riga[3] = sim
                # ~0.5 e' il caso; sopra 0.8 e' quasi certamente lei.
                riga[0] += max(0.0, sim - 0.55) * 40
        punteggi.sort(key=lambda x: -x[0])

    # Un tuo scan confermato che somiglia a questo vale piu' di qualsiasi
    # indizio: stesso scanner, stessa luce. 0.95 → +12, 0.85 → +4.
    if gia_viste:
        for riga in punteggi:
            ref = gia_viste.get(riga[1].id)
            if ref:
                riga[0] += max(0.0, ref - SOGLIA_GIA_VISTA) * 80
        punteggi.sort(key=lambda x: -x[0])

    _penalita_edizione(db, punteggi, lettura.language)

    candidati = [
        {
            "blueprint_id": bp.id,
            "name": bp.name,
            "version": bp.version,
            "number": bp.collector_number,
            "expansion_id": bp.expansion_id,
            "expansion_code": bp.expansion_code,
            "expansion_name": bp.expansion_name,
            "image_url": bp.image_url,
            "score": round(s, 1),
            "number_match": num == 2,
            "image_similarity": round(sim, 3) if sim is not None else None,
            # Somiglianza con un tuo scan gia' confermato di questa carta
            "seen_before": round(gia_viste[bp.id], 3) if bp.id in gia_viste else None,
        }
        for s, bp, num, sim in punteggi[:MAX_CANDIDATI]
    ]
    confidenza = _confidenza(candidati)
    nota = _nota_varianti(candidati)
    if nota and confidenza == "alta":
        confidenza = "media"
    return {"candidates": candidati, "confidence": confidenza, "note": nota}


def _stessa_carta_altra_versione(a: dict, b: dict) -> bool:
    """Arte alternativa, rarita' diversa, ristampa corretta (stessa
    espansione, stesso nome o numero con suffisso: OP01-064 / OP01-064b),
    oppure la stessa carta ristampata in un altro set (promo, Premium
    Booster): stesso numero e stesso nome."""
    na, nb = _norm_number(a["number"]), _norm_number(b["number"])
    if a["expansion_id"] != b["expansion_id"]:
        return bool(na) and na == nb and _tokens(a["name"])[:2] == _tokens(b["name"])[:2]
    if a["name"] == b["name"]:
        return True
    return bool(na and nb) and (na.startswith(nb) or nb.startswith(na))


def _nota_varianti(c: List[dict]) -> Optional[str]:
    """Se in testa ci sono due versioni della stessa carta e l'immagine non
    le separa bene, lo si dice: e' li' che si sbaglia la versione (o il
    set, per le ristampe con la stessa illustrazione)."""
    if len(c) < 2:
        return None
    primo = c[0]
    for altro in c[1:]:
        altro["variant_of_top"] = _stessa_carta_altra_versione(primo, altro)
    varianti = [x for x in c[1:] if x.get("variant_of_top")]
    if not varianti:
        return None
    # Gia' vista e confermata proprio in questa versione: la memoria ha
    # gia' deciso, a meno che anche l'altra versione sia stata vista.
    gv = primo.get("seen_before") or 0
    if gv >= SOGLIA_GIA_VISTA_SICURA and all((v.get("seen_before") or 0) < gv - 0.03 for v in varianti):
        return None
    sp = primo.get("image_similarity") or 0
    vicine = [v for v in varianti if sp - (v.get("image_similarity") or 0) < 0.04]
    if not vicine:
        return None

    def etichetta(v):
        if v["expansion_id"] != primo["expansion_id"]:
            return f"{v['number']} in {v['expansion_name']}"
        return f"{v['number']}{' ' + v['version'] if v.get('version') else ''}"

    return ("Altre versioni quasi identiche: " + ", ".join(etichetta(v) for v in vicine[:3])
            + " — controlla arte, rarità e simbolo del set")


RE_EDIZIONI_RARE = re.compile(r"world championship", re.I)
CONFRONTI_LINGUA = 15


def _penalita_edizione(db: Session, punteggi: list, lingua: Optional[str]) -> None:
    """Fra versioni con la stessa immagine decidono gli indizi deboli:
    - la lingua letta sullo scan esclude i set che in quella lingua non
      sono mai usciti (un'italiana non e' del set solo giapponese);
    - le ristampe dei World Championship Decks (retro diverso, non
      legali, rare in collezione) passano dietro alla stampa normale."""
    for riga in punteggi[:CONFRONTI_LINGUA]:
        bp = riga[1]
        if RE_EDIZIONI_RARE.search(bp.expansion_name or ""):
            riga[0] -= 2
        if lingua:
            try:
                disponibili = lingue(editable_for(db, bp))
            except Exception as exc:  # noqa: BLE001 — indizio facoltativo
                db.rollback()
                LOGGER.info("Lingue del blueprint %s non disponibili: %s", bp.id, exc)
                disponibili = None
            if disponibili is not None and lingua not in disponibili:
                # Set senza scelta di lingua: di solito asiatico, ma non e'
                # detto → penalita' piu' leggera.
                riga[0] -= 8 if disponibili else 5
    punteggi.sort(key=lambda x: -x[0])


# Sopra questa somiglianza con un tuo scan confermato, e' quasi certamente
# la stessa carta (fra ristampe diverse due scan arrivano a ~0.9).
SOGLIA_GIA_VISTA = 0.80
SOGLIA_GIA_VISTA_SICURA = 0.93


def _confidenza(c: List[dict]) -> str:
    if not c:
        return "bassa"
    primo = c[0]
    stacco = primo["score"] - (c[1]["score"] if len(c) > 1 else 0)
    immagine = primo.get("image_similarity") or 0
    if (primo.get("seen_before") or 0) >= SOGLIA_GIA_VISTA_SICURA and stacco >= 6:
        return "alta"
    if primo["number_match"] and stacco >= 6 and immagine >= 0.7:
        return "alta"
    if (primo["number_match"] or immagine >= 0.75) and stacco >= 3:
        return "media"
    return "bassa"
