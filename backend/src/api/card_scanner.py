"""
Scanner carte: dagli scan alla collezione, dalla collezione alla vendita.

Il giro:
1. si caricano gli scan (uno per richiesta: l'interfaccia li manda in
   fila e mostra l'avanzamento, l'OCR costa qualche secondo a carta);
2. per ogni scan si propongono i blueprint CardTrader candidati;
3. una persona conferma (o corregge) → la carta entra nella collezione
   (personal_cards) e viene valutata: CardTrader + venduti eBay;
4. dalla collezione si mette in vendita su CardTrader e/o eBay, e la si
   esporta in CSV.

Admin-only. NB: NIENTE `from __future__ import annotations` (vedi api/orders.py).
"""
import csv
import io
import logging
import zipfile
from datetime import date
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.personal_cards import _to_response
from helpers.auth import require_admin
from models.db import CardScan, CardScanStatus, PersonalCard, PersonalCardStatus, User
from models.db.card_scan import CardBlueprint
from models.entities.personal_card import PersonalCardResponse
from utils import card_features as cf
from utils import card_index as ci
from utils import card_learning as learn
from utils import card_listing as cl
from utils import card_ocr
from utils import card_pricing as cp
from utils import cardtrader_client as ct
from utils import ebay_client as eb
from utils import storage
from utils.cardtrader_sync import _default_game_id, _default_language, _norm_number
from utils.session import SessionLocal, get_db

LOGGER = logging.getLogger("card_scanner")

router = APIRouter(prefix="/api/card-scanner", tags=["card-scanner"])


def _guard_cardtrader():
    if not ct.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CardTrader non configurato: manca CARDTRADER_JWT.",
        )


def _card_or_404(db: Session, card_id: int) -> PersonalCard:
    card = db.query(PersonalCard).filter(PersonalCard.id == card_id).first()
    if not card:
        raise HTTPException(404, f"Carta {card_id} non trovata")
    return card


def _scan_or_404(db: Session, scan_id: int) -> CardScan:
    scan = db.query(CardScan).filter(CardScan.id == scan_id).first()
    if not scan:
        raise HTTPException(404, f"Scan {scan_id} non trovato")
    return scan


# ── Sessione di scansione ─────────────────────────────────────────
#
# Gioco ed espansione scelti nella pagina valgono anche per gli scan che
# arrivano dalla cartella osservata (scripts/scanner_watch.py): chi
# scansiona sceglie una volta, nella pagina, e lo script non deve sapere
# niente.

def _int_setting(db: Session, key: str) -> Optional[int]:
    from helpers.setting import SettingHelper
    v = (SettingHelper(db=db).get_value(key) or "").strip()
    return int(v) if v.isdigit() else None


def _sessione(db: Session) -> dict:
    return {
        "game_id": _int_setting(db, "card_scanner_game_id") or _default_game_id(db),
        "expansion_id": _int_setting(db, "card_scanner_expansion_id"),
    }


class SessionRequest(BaseModel):
    game_id: int = Field(..., ge=1)
    expansion_id: Optional[int] = Field(None, ge=1)


@router.put("/session")
def set_session(payload: SessionRequest, db: Session = Depends(get_db),
                _admin: User = Depends(require_admin)):
    from helpers.setting import SettingHelper
    h = SettingHelper(db=db)
    h.upsert("card_scanner_game_id", str(payload.game_id))
    h.upsert("card_scanner_expansion_id", str(payload.expansion_id or ""))
    return _sessione(db)


# ── Stato e indice ────────────────────────────────────────────────

@router.get("/status")
def scanner_status(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Cosa c'e' e cosa manca: OCR, CardTrader, eBay, indice per gioco."""
    return {
        "ocr": card_ocr.is_available(),
        "cardtrader": ct.is_configured(),
        "ebay_sold": eb.has_app_credentials(),
        "ebay_publish": eb.is_configured(),
        "ebay_env": "sandbox" if eb.is_sandbox() else "production",
        "default_game_id": _default_game_id(db),
        "default_language": _default_language(db),
        "session": _sessione(db),
        "index": ci.build_status(db),
        "learning": learn.status(db),
        "pending_scans": db.query(CardScan).filter(CardScan.status == CardScanStatus.PENDING).count(),
    }


class IndexBuildRequest(BaseModel):
    game_id: int = Field(..., ge=1)
    # True = riscarica anche le espansioni gia' in indice (nuove carte
    # aggiunte a un set uscito da poco).
    full: bool = False


@router.post("/index/build")
def index_build(payload: IndexBuildRequest, _admin: User = Depends(require_admin)):
    """Costruisce l'indice del gioco in background (qualche minuto: un
    export CardTrader per espansione). Si segue da /status."""
    _guard_cardtrader()
    avviato = ci.start_build(payload.game_id, SessionLocal, full=payload.full)
    return {"started": avviato, "detail": None if avviato else "Indice gia' in costruzione"}


# ── Scan ──────────────────────────────────────────────────────────

class ScanResponse(BaseModel):
    id: int
    image_url: str
    original_filename: Optional[str] = None
    game_id: Optional[int] = None
    expansion_id: Optional[int] = None
    status: str
    ocr: dict = {}
    candidates: List[dict] = []
    confidence: Optional[str] = None
    note: Optional[str] = None
    back_image_url: Optional[str] = None
    # Analisi della carta scelta: {blueprint_id, reverse, first_edition,
    # condition, supports}
    features: dict = {}
    error: Optional[str] = None
    personal_card_id: Optional[int] = None


def _scan_response(scan: CardScan) -> ScanResponse:
    return ScanResponse(
        id=scan.id, image_url=scan.image_url, original_filename=scan.original_filename,
        game_id=scan.game_id, expansion_id=scan.expansion_id, status=scan.status,
        ocr=scan.ocr or {}, candidates=scan.candidates or [], confidence=scan.confidence,
        note=(scan.ocr or {}).get("variant_note"), back_image_url=scan.back_image_url,
        features=scan.features or {}, error=scan.error, personal_card_id=scan.personal_card_id,
    )


def _riconosci(db: Session, scan: CardScan, card_img, lettura) -> None:
    """Abbina e salva l'esito sullo scan. Un errore qui non perde lo scan:
    resta in coda con l'errore, e si riprova o si cerca a mano."""
    try:
        impronta = ci.dhash(card_img)
        scan.dhash = scan.dhash or impronta
        esito = ci.match(db, scan.game_id, lettura, impronta, scan.expansion_id,
                         appreso=learn.confusions(db, scan.game_id))
        scan.candidates = esito["candidates"]
        scan.confidence = esito["confidence"]
        scan.ocr = {**lettura.as_dict(), "variant_note": esito.get("note")}
        scan.error = None if esito["candidates"] else "Nessun candidato: cerca la carta a mano"
        if esito["candidates"]:
            _analizza(db, scan, esito["candidates"][0]["blueprint_id"], card_img)
    except ct.CardTraderError as exc:
        db.rollback()
        scan.error = f"CardTrader: {exc}"
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        LOGGER.exception("Riconoscimento scan %s fallito", scan.id)
        scan.error = str(exc)
    db.commit()


def _immagine_salvata(url: Optional[str]):
    path = storage.path_from_internal_url(url) if url else None
    if not path or not path.exists():
        return None
    with open(path, "rb") as fh:
        return card_ocr.load_image(fh.read())


def _analizza(db: Session, scan: CardScan, blueprint_id: int, card_img=None) -> None:
    """Reverse, prima edizione e condizione per la carta scelta. Best
    effort: se fallisce lo scan resta confermabile a mano."""
    bp = db.query(CardBlueprint).filter(CardBlueprint.id == blueprint_id).first()
    if not bp:
        return
    try:
        fronte = card_img if card_img is not None else _immagine_salvata(scan.image_url)
        if fronte is None:
            return
        analisi = cf.analyze(
            fronte,
            ci.GAME_HINTS.get(bp.game_id),
            ci.editable_for(db, bp),
            bp.image_url,
            testo_ocr=(scan.ocr or {}).get("full_text", ""),
            retro=_immagine_salvata(scan.back_image_url),
            tarate=learn.load_thresholds(db),
        )
        scan.features = {"blueprint_id": bp.id, **analisi}
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        LOGGER.warning("Analisi scan %s fallita: %s", scan.id, exc)
        scan.features = {"blueprint_id": bp.id, "error": str(exc)}
    db.commit()


@router.post("/scans", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
def upload_scan(
    file: UploadFile = File(...),
    game_id: Optional[int] = Form(None),
    expansion_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Uno scan → ritaglio, OCR, candidati. Si salva la carta ritagliata e
    raddrizzata: e' quella che finisce in collezione e nelle inserzioni."""
    _guard_cardtrader()
    if not card_ocr.is_available():
        raise HTTPException(503, "Tesseract non installato sul server")
    if not game_id:
        # Dalla cartella osservata: valgono le scelte fatte nella pagina.
        sessione = _sessione(db)
        game_id = sessione["game_id"]
        expansion_id = expansion_id or sessione["expansion_id"]
    if not game_id:
        raise HTTPException(400, "Scegli il gioco")

    try:
        raw = storage._read_with_limit(file.file)
        card_img, lettura = card_ocr.read_card(raw, ci.GAME_HINTS.get(game_id),
                                               learn.confusions(db, game_id))
    except storage.UploadValidationError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Immagine non leggibile: {exc}") from exc

    scan = CardScan(
        image_url="", original_filename=(file.filename or "")[:255],
        game_id=game_id, expansion_id=expansion_id,
        status=CardScanStatus.PENDING, ocr=lettura.as_dict(), candidates=[],
    )
    db.add(scan)
    db.commit()

    buf = io.BytesIO()
    card_img.save(buf, format="JPEG", quality=92)
    buf.seek(0)
    scan.image_url, _ = storage.save_upload("scans", scan.id, buf, "image/jpeg")
    db.commit()

    _riconosci(db, scan, card_img, lettura)
    return _scan_response(scan)


@router.get("/scans", response_model=List[ScanResponse])
def list_scans(
    status_filter: str = Query(CardScanStatus.PENDING, alias="status"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    scans = (
        db.query(CardScan).filter(CardScan.status == status_filter)
        .order_by(CardScan.id).limit(500).all()
    )
    return [_scan_response(s) for s in scans]


class RematchRequest(BaseModel):
    """Correzioni a mano quando l'OCR ha letto male."""
    expansion_id: Optional[int] = None
    number: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=200)


@router.post("/scans/{scan_id}/rematch", response_model=ScanResponse)
def rematch_scan(
    scan_id: int,
    payload: RematchRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    _guard_cardtrader()
    scan = _scan_or_404(db, scan_id)
    img = _immagine_salvata(scan.image_url)
    if img is None:
        raise HTTPException(410, "File dello scan non piu' disponibile")
    lettura = card_ocr.LetturaCarta(**{
        k: v for k, v in (scan.ocr or {}).items()
        if k in card_ocr.LetturaCarta.__dataclass_fields__
    })
    if payload.number is not None:
        lettura.number = payload.number.strip() or None
        lettura.total = None
    if payload.name is not None:
        lettura.name_text = payload.name
        lettura.full_text = payload.name
    if payload.expansion_id is not None:
        scan.expansion_id = payload.expansion_id or None
    scan.ocr = lettura.as_dict()
    _riconosci(db, scan, img, lettura)
    return _scan_response(scan)


class FeaturesRequest(BaseModel):
    blueprint_id: int = Field(..., ge=1)


@router.post("/scans/{scan_id}/features", response_model=ScanResponse)
def analyze_scan(
    scan_id: int,
    payload: FeaturesRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Rifa l'analisi per un altro candidato: reverse e prima edizione si
    misurano rispetto all'immagine della carta scelta."""
    scan = _scan_or_404(db, scan_id)
    _analizza(db, scan, payload.blueprint_id)
    return _scan_response(scan)


@router.post("/scans/{scan_id}/back", response_model=ScanResponse)
def upload_back(
    scan_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Il retro della carta: l'usura dei bordi si vede soprattutto li'.
    Finisce anche fra le foto della carta (eBay lo apprezza)."""
    scan = _scan_or_404(db, scan_id)
    try:
        retro = card_ocr.prepare(storage._read_with_limit(file.file))
    except storage.UploadValidationError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Immagine non leggibile: {exc}") from exc
    buf = io.BytesIO()
    retro.save(buf, format="JPEG", quality=92)
    buf.seek(0)
    if scan.back_image_url:
        storage.delete_file_for_url(scan.back_image_url)
    scan.back_image_url, _ = storage.save_upload("scans", scan.id, buf, "image/jpeg")
    # Retro arrivato dopo la conferma (lo script giornaliero, un giorno
    # dopo il fronte): va anche fra le foto della carta.
    if scan.personal_card_id:
        card = db.query(PersonalCard).filter(PersonalCard.id == scan.personal_card_id).first()
        if card is not None:
            card.images = [u for u in (card.images or []) if u] + [scan.back_image_url]
    db.commit()
    bp_id = (scan.features or {}).get("blueprint_id") or (
        scan.candidates[0]["blueprint_id"] if scan.candidates else None)
    if bp_id:
        _analizza(db, scan, bp_id)
    return _scan_response(scan)


class ConfirmRequest(BaseModel):
    """Condizione, reverse e prima edizione: se non li si dice, valgono
    quelli dell'analisi dello scan (quando e' sicura)."""
    blueprint_id: int = Field(..., ge=1)
    condition: Optional[str] = Field(None, max_length=20)
    language: Optional[str] = Field(None, max_length=5)
    quantity: int = Field(1, ge=1, le=999)
    reverse: Optional[bool] = None
    first_edition: Optional[bool] = None
    # Valutare subito costa due chiamate esterne: con tanti scan si puo'
    # rimandare e valutare in blocco dalla collezione.
    price_now: bool = True


@router.post("/scans/{scan_id}/confirm", response_model=PersonalCardResponse)
def confirm_scan(
    scan_id: int,
    payload: ConfirmRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Lo scan diventa una carta della collezione."""
    scan = _scan_or_404(db, scan_id)
    if scan.status != CardScanStatus.PENDING:
        raise HTTPException(409, "Scan gia' confermato o scartato")
    bp = db.query(CardBlueprint).filter(CardBlueprint.id == payload.blueprint_id).first()
    if not bp:
        raise HTTPException(400, "Blueprint non in indice: rifai la ricerca")

    letto = scan.ocr or {}
    # Il codice stampato vale solo se e' quello della carta scelta: se la
    # persona ha corretto il numero, quello letto e' sbagliato.
    stampato = letto.get("printed_code")
    if stampato and _norm_number(letto.get("number")) != bp.number_norm:
        # Il totale ("/191") di solito e' letto bene anche quando il numero
        # no: si ricompone col numero giusto, e' cio' che si cerca su eBay.
        stampato = f"{bp.collector_number}/{letto['total']}" if letto.get("total") else None

    # L'analisi vale solo se e' stata fatta su questa carta.
    analisi = scan.features or {}
    if analisi.get("blueprint_id") != bp.id:
        analisi = {}

    def dall_analisi(chiave):
        return bool((analisi.get(chiave) or {}).get("value"))

    condizione = payload.condition or (analisi.get("condition") or {}).get("value") or "Near Mint"
    reverse = payload.reverse if payload.reverse is not None else dall_analisi("reverse")
    prima = payload.first_edition if payload.first_edition is not None else dall_analisi("first_edition")

    card = PersonalCard(
        name=bp.name,
        collection=bp.expansion_name,
        card_number=bp.collector_number,
        printed_code=stampato or bp.collector_number,
        language=(payload.language or letto.get("language") or _default_language(db) or "it").lower(),
        condition=condizione,
        quantity=payload.quantity,
        status=PersonalCardStatus.IN_STOCK,
        images=[u for u in (scan.image_url, scan.back_image_url) if u],
        game_id=bp.game_id,
        cardtrader_blueprint_id=bp.id,
        cardtrader_expansion_id=bp.expansion_id,
        reverse=reverse,
        first_edition=prima,
        purchase_date=date.today(),
        purchase_source="scanner",
    )
    db.add(card)
    db.commit()
    scan.status = CardScanStatus.CONFIRMED
    scan.personal_card_id = card.id
    db.commit()

    # Quello che la conferma insegna: lo scan diventa un riferimento della
    # carta, gli errori dell'OCR si contano, le soglie si ritarano.
    if not scan.dhash:
        img = _immagine_salvata(scan.image_url)
        scan.dhash = ci.dhash(img) if img is not None else None
    learn.learn_from_confirmation(db, scan, card, bp.expansion_code or "")

    if payload.price_now:
        try:
            cp.price_card(card)
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            LOGGER.warning("Valutazione carta %s fallita: %s", card.id, exc)
    db.refresh(card)
    return _to_response(card)


class AutoConfirmResponse(BaseModel):
    confirmed: bool
    reason: Optional[str] = None
    card: Optional[PersonalCardResponse] = None
    scan: ScanResponse


@router.post("/scans/{scan_id}/auto-confirm", response_model=AutoConfirmResponse)
def auto_confirm_scan(
    scan_id: int,
    price_now: bool = Query(True),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Conferma da sola, senza una persona, SOLO se il riconoscimento e'
    sicuro: confidenza alta e nessuna altra versione quasi identiche.
    Tutto il resto resta in coda per la pagina: una carta sbagliata in
    collezione costa piu' di una conferma a mano. Lo usa lo script che
    carica la cartella dello scanner una volta al giorno."""
    scan = _scan_or_404(db, scan_id)
    if scan.status != CardScanStatus.PENDING:
        return AutoConfirmResponse(confirmed=False, reason="gia' confermato o scartato",
                                   scan=_scan_response(scan))
    if not scan.candidates:
        motivo = "nessun candidato"
    elif scan.confidence != "alta":
        motivo = f"confidenza {scan.confidence or 'bassa'}"
    elif (scan.ocr or {}).get("variant_note"):
        motivo = "altre versioni quasi identiche"
    else:
        motivo = None
    if motivo:
        return AutoConfirmResponse(confirmed=False, reason=motivo, scan=_scan_response(scan))
    carta = confirm_scan(
        scan_id,
        ConfirmRequest(blueprint_id=scan.candidates[0]["blueprint_id"], price_now=price_now),
        db=db, _admin=_admin,
    )
    return AutoConfirmResponse(confirmed=True, card=carta, scan=_scan_response(scan))


@router.delete("/scans/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
def discard_scan(scan_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    scan = _scan_or_404(db, scan_id)
    if scan.status == CardScanStatus.PENDING:
        scan.status = CardScanStatus.DISCARDED
        db.commit()
        for url in (scan.image_url, scan.back_image_url):
            if url:
                storage.delete_file_for_url(url)
    return None


@router.get("/blueprints/search")
def search_blueprints(
    game_id: int = Query(...),
    q: str = Query(..., min_length=2),
    expansion_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Ricerca a mano nell'indice, per nome o numero."""
    query = db.query(CardBlueprint).filter(CardBlueprint.game_id == game_id)
    if expansion_id:
        query = query.filter(CardBlueprint.expansion_id == expansion_id)
    query = query.filter(or_(
        CardBlueprint.name.ilike(f"%{q.strip()}%"),
        CardBlueprint.number_norm == _norm_number(q),
    ))
    return [
        {"blueprint_id": b.id, "name": b.name, "version": b.version, "number": b.collector_number,
         "expansion_id": b.expansion_id, "expansion_name": b.expansion_name,
         "expansion_code": b.expansion_code, "image_url": b.image_url}
        for b in query.order_by(CardBlueprint.name).limit(40)
    ]


# ── Collezione ────────────────────────────────────────────────────

@router.get("/cards", response_model=List[PersonalCardResponse])
def list_cards(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Le carte abbinate a CardTrader (quelle passate dallo scanner o
    abbinate a mano): il catalogo di cio' che si ha."""
    q = db.query(PersonalCard).filter(PersonalCard.cardtrader_blueprint_id.isnot(None))
    if status_filter:
        q = q.filter(PersonalCard.status == status_filter)
    if search and search.strip():
        t = f"%{search.strip()}%"
        q = q.filter(or_(PersonalCard.name.ilike(t), PersonalCard.collection.ilike(t),
                         PersonalCard.printed_code.ilike(t)))
    return [_to_response(c) for c in q.order_by(PersonalCard.id.desc()).limit(2000)]


@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(card_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Toglie la carta dalla collezione, con i suoi scan.

    Se e' in vendita su CardTrader o eBay ci si ferma: cancellarla qui
    lascerebbe l'inserzione viva senza piu' niente che la ricordi, e la
    carta si potrebbe vendere senza averla. Prima si ritira."""
    card = _card_or_404(db, card_id)
    sul_sito = card.article is not None and card.article.status.value == "PUBLISHED"
    in_vendita = [n for n, v in (("CardTrader", card.cardtrader_product_id),
                                 ("eBay", card.ebay_listing_id), ("sito", sul_sito)) if v]
    if in_vendita:
        raise HTTPException(409, f"La carta e' in vendita su {' e '.join(in_vendita)}: ritirala prima")
    file = list(card.images or [])
    for scan in db.query(CardScan).filter(CardScan.personal_card_id == card.id):
        file += [scan.image_url, scan.back_image_url]
        db.delete(scan)
    db.delete(card)
    db.commit()
    for url in {u for u in file if u}:
        storage.delete_file_for_url(url)
    return None


# ── Collezione: prezzi ────────────────────────────────────────────

class PricedResponse(BaseModel):
    card: PersonalCardResponse
    warnings: dict = {}
    ebay_sold_url: str


@router.post("/cards/{card_id}/price", response_model=PricedResponse)
def price_card(card_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    card = _card_or_404(db, card_id)
    avvisi = cp.price_card(card)
    db.commit()
    db.refresh(card)
    return PricedResponse(card=_to_response(card), warnings=avvisi, ebay_sold_url=cp.ebay_sold_url(card))


class ManualSoldRequest(BaseModel):
    """Prezzi dei venduti copiati dalla ricerca eBay, separati da spazi,
    a capo o punto e virgola. Vuoto = torna a leggerli dall'API."""
    prices: str = Field("", max_length=2000)


@router.post("/cards/{card_id}/ebay-sold", response_model=PricedResponse)
def manual_ebay_sold(
    card_id: int,
    payload: ManualSoldRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    card = _card_or_404(db, card_id)
    prezzi = cp.parse_manual_prices(payload.prices)
    if prezzi:
        # Nell'ordine incollato: i primi sono i piu' recenti, come li
        # mostra eBay ordinando per "conclusi di recente".
        vendite = [{"title": None, "price": p, "date": None, "url": None} for p in prezzi]
        riepilogo = {
            "avg": round(sum(prezzi[:cp.ULTIME_VENDITE]) / len(prezzi[:cp.ULTIME_VENDITE]), 2),
            "count": len(prezzi[:cp.ULTIME_VENDITE]),
            "sales": vendite[:cp.ULTIME_VENDITE],
        }
        cp.apply_ebay(card, riepilogo, "manuale")
    else:
        cp.apply_ebay(card, None, "api")
    cp.refresh_suggested(card)
    db.commit()
    db.refresh(card)
    return PricedResponse(card=_to_response(card), warnings={}, ebay_sold_url=cp.ebay_sold_url(card))


@router.get("/cards/{card_id}/ebay-sold-url")
def ebay_sold_url(card_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return {"url": cp.ebay_sold_url(_card_or_404(db, card_id))}


# ── Collezione: vendita ───────────────────────────────────────────

def _esegui(fn, db: Session, card: PersonalCard):
    try:
        return fn(db, card)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except (ct.CardTraderError, eb.EbayError) as exc:
        db.rollback()
        detail = f"{exc} (body={exc.body})" if getattr(exc, "body", None) else str(exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail) from exc


@router.post("/cards/{card_id}/cardtrader")
def publish_cardtrader(card_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    _guard_cardtrader()
    return _esegui(cl.publish_cardtrader, db, _card_or_404(db, card_id))


@router.delete("/cards/{card_id}/cardtrader")
def unpublish_cardtrader(card_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    _guard_cardtrader()
    _esegui(cl.unpublish_cardtrader, db, _card_or_404(db, card_id))
    return {"ok": True}


@router.post("/cards/{card_id}/site")
def publish_site(card_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """In vetrina sul sito, con le foto dello scan."""
    return _esegui(lambda d, c: cl.publish_site(d, c, _admin.id), db, _card_or_404(db, card_id))


@router.delete("/cards/{card_id}/site")
def unpublish_site(card_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    _esegui(cl.unpublish_site, db, _card_or_404(db, card_id))
    return {"ok": True}


@router.post("/cards/{card_id}/ebay")
def publish_ebay(card_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return _esegui(cl.publish_ebay, db, _card_or_404(db, card_id))


@router.delete("/cards/{card_id}/ebay")
def unpublish_ebay(card_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    _esegui(cl.unpublish_ebay, db, _card_or_404(db, card_id))
    return {"ok": True}


# ── Collezione: CSV ───────────────────────────────────────────────

COLONNE_CSV = [
    ("id", lambda c: c.id),
    ("nome", lambda c: c.name),
    ("espansione", lambda c: c.collection),
    ("numero", lambda c: c.printed_code or c.card_number),
    ("lingua", lambda c: c.language),
    ("condizione", lambda c: c.condition),
    ("quantita", lambda c: c.quantity),
    ("prima_edizione", lambda c: "si" if c.first_edition else ""),
    ("reverse", lambda c: "si" if c.reverse else ""),
    ("stato", lambda c: c.status),
    ("prezzo_cardtrader", lambda c: c.cardtrader_price),
    ("media_venduti_ebay", lambda c: c.ebay_sold_avg),
    ("n_venduti_ebay", lambda c: c.ebay_sold_count),
    ("prezzo_suggerito", lambda c: c.estimated_value),
    ("prezzo_vendita", lambda c: c.list_price),
    ("costo_acquisto", lambda c: c.purchase_cost),
    ("in_vendita_cardtrader", lambda c: "si" if c.cardtrader_product_id else ""),
    ("in_vendita_ebay", lambda c: "si" if c.ebay_listing_id else ""),
    ("cardtrader_blueprint_id", lambda c: c.cardtrader_blueprint_id),
    ("valutata_il", lambda c: c.prices_updated_at.date().isoformat() if c.prices_updated_at else ""),
    ("scan", lambda c: (c.images or [""])[0]),
    ("note", lambda c: c.notes),
]


def _cella(v) -> str:
    if v is None:
        return ""
    # Excel italiano: virgola decimale, cosi' i prezzi restano numeri.
    if hasattr(v, "quantize"):
        return f"{v:.2f}".replace(".", ",")
    return str(v)


@router.get("/cards/export.csv")
def export_csv(
    status_filter: Optional[str] = Query(None, alias="status"),
    only_scanned: bool = Query(False),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """La collezione in CSV (separatore ; per Excel italiano, con BOM per
    gli accenti)."""
    q = db.query(PersonalCard)
    if status_filter:
        q = q.filter(PersonalCard.status == status_filter)
    if only_scanned:
        q = q.filter(PersonalCard.cardtrader_blueprint_id.isnot(None))
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")
    w.writerow([nome for nome, _ in COLONNE_CSV])
    for c in q.order_by(PersonalCard.collection, PersonalCard.card_number, PersonalCard.id):
        w.writerow([_cella(f(c)) for _, f in COLONNE_CSV])
    nome = f"collezione-carte-{date.today().isoformat()}.csv"
    return Response(
        content="﻿" + out.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


# ── Pacchetto per Windows ─────────────────────────────────────────

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
# (file nel repo, nome nello ZIP)
FILE_PACCHETTO = [
    ("scanner_sync.py", "scanner_sync.py"),
    ("installa-scanner-sync.ps1", "installa-scanner-sync.ps1"),
    ("windows/Installa.cmd", "Installa.cmd"),
    ("windows/Installa.ps1", "Installa.ps1"),
    ("windows/Disinstalla.cmd", "Disinstalla.cmd"),
    ("windows/Disinstalla.ps1", "Disinstalla.ps1"),
    ("windows/LEGGIMI.txt", "LEGGIMI.txt"),
]


def _a_capo_windows(testo: str) -> bytes:
    """I .cmd con gli a capo Unix su certi Windows saltano le righe; il
    Blocco note vecchio mostra tutto su una riga. Meglio CRLF ovunque."""
    return testo.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")


@router.get("/windows-kit")
def windows_kit(_admin: User = Depends(require_admin)):
    """Lo ZIP da scaricare sul PC dello scanner: script, installazione
    guidata, e l'indirizzo di questo sito gia' scritto dentro. Nessuna
    password: il file si scarica e puo' girare."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for sorgente, nome in FILE_PACCHETTO:
            dati = (SCRIPTS / sorgente).read_text(encoding="utf-8")
            if not nome.endswith(".py"):
                dati = _a_capo_windows(dati)
            z.writestr(f"NerdNostalgia-Scanner/{nome}", dati)
        z.writestr(
            "NerdNostalgia-Scanner/predefiniti.ini",
            _a_capo_windows(
                "; Scritto dal sito quando hai scaricato il pacchetto.\n"
                "[scanner]\n"
                f"api = {storage.BASE_URL}\n"
                "auto_conferma = si\n"
                "valuta_subito = si\n"
            ),
        )
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="NerdNostalgia-Scanner-Windows.zip"'},
    )
