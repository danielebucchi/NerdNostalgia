"""
Caricamento massivo di carte.

Serve a svuotare una scatola in fretta: niente foto, niente schede
curate, niente pubblicazione sul sito. Le carte nascono come articoli in
bozza — restano in inventario per la contabilita' ma non compaiono in
catalogo — e vanno dritte in vendita su CardTrader.

Il prezzo non si decide a mano: lo si prende dal mercato, alla posizione
richiesta (di norma il SECONDO piu' basso) fra le inserzioni con la
stessa condizione e la stessa lingua. Confrontare una Near Mint italiana
col prezzo di una Played inglese darebbe un numero senza senso.

Due strade di ingresso, perche' servono a due momenti diversi:
- blueprint gia' scelto, quando si inserisce dall'interfaccia con
  l'espansione fissa e la ricerca per nome;
- testo CSV, quando l'elenco esiste gia' da un'altra parte. Li' i nomi
  vanno prima RISOLTI in blueprint, e la risoluzione la conferma una
  persona: un nome che somiglia non e' un nome che coincide.

NB: NIENTE `from __future__ import annotations` (vedi api/orders.py).
"""
import csv
import io
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from models.db import Article, ArticleStatus, User
from utils import cardtrader_client as ct
from utils import cardtrader_sync as cts
from utils.session import get_db

LOGGER = logging.getLogger("bulk_cards")

router = APIRouter(prefix="/api/cards/bulk", tags=["cards-bulk"])

# Ogni riga costa due chiamate a CardTrader (prezzo + inserzione), quindi
# un lotto grosso terrebbe la richiesta aperta per minuti. L'interfaccia
# manda a pezzi e mostra l'avanzamento: meglio tanti lotti brevi che uno
# lungo che non si sa a che punto sia.
MAX_RIGHE = 50


def _guard():
    if not ct.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CardTrader non configurato: manca CARDTRADER_JWT.",
        )


class BulkRow(BaseModel):
    """Una carta da caricare."""
    blueprint_id: int = Field(..., ge=1)
    # Serve solo a dare un titolo leggibile all'articolo in inventario.
    name: Optional[str] = Field(None, max_length=255)
    number: Optional[str] = Field(None, max_length=50)
    collection: Optional[str] = Field(None, max_length=100)

    quantity: int = Field(1, ge=1, le=999)
    condition: str = Field("Near Mint", max_length=30)
    language: Optional[str] = Field(None, max_length=5)
    reverse: bool = False
    first_edition: bool = False


class BulkPublishRequest(BaseModel):
    # 2 = secondo prezzo piu' basso. Resta un parametro perche' la
    # posizione giusta cambia con quanto si vuole stare sotto mercato.
    price_position: int = Field(2, ge=1, le=20)
    rows: List[BulkRow] = Field(..., min_length=1, max_length=MAX_RIGHE)


class RowOutcome(BaseModel):
    index: int
    ok: bool
    article_id: Optional[int] = None
    product_id: Optional[int] = None
    price_eur: Optional[float] = None
    price_position: Optional[int] = None
    price_total_offers: Optional[int] = None
    error: Optional[str] = None


def _titolo(row: BulkRow) -> str:
    """Titolo dell'articolo in inventario. Non finisce sul sito (la carta
    resta in bozza): serve a riconoscerla in elenco."""
    parti = [row.name or f"Blueprint {row.blueprint_id}"]
    if row.number:
        parti.append(f"#{row.number}")
    if row.collection:
        parti.append(f"({row.collection})")
    return " ".join(parti)[:255]


@router.post("/publish", response_model=List[RowOutcome])
def bulk_publish(
    payload: BulkPublishRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Crea un articolo in bozza per ogni riga e lo mette in vendita su
    CardTrader al prezzo di mercato richiesto.

    Ogni riga va per conto suo: una carta che non si riesce a prezzare non
    deve far fallire le altre quarantanove gia' inserite.
    """
    _guard()
    esiti: List[RowOutcome] = []

    for i, row in enumerate(payload.rows):
        article = None
        try:
            article = Article(
                # L'articolo e' di chi lo carica: la colonna non ammette
                # NULL, e in inventario si deve sapere chi ha inserito cosa.
                user_id=_admin.id,
                title=_titolo(row),
                # Il prezzo vero arriva dal mercato un attimo dopo; qui serve
                # un valore perche' la colonna non ammette NULL.
                price=0,
                quantity=row.quantity,
                # In bozza: la carta non compare in catalogo, ma esiste in
                # inventario e nei conti.
                status=ArticleStatus.DRAFT,
                card_collection=row.collection,
                card_number=row.number,
                card_condition=row.condition,
                card_language=row.language,
                card_reverse=row.reverse,
                card_first_edition=row.first_edition,
                cardtrader_blueprint_id=row.blueprint_id,
            )
            db.add(article)
            db.commit()
            db.refresh(article)

            esito = cts.publish_article(
                db, article,
                price_position=payload.price_position,
                quantity=row.quantity,
                condition=row.condition,
                language=row.language,
                reverse=row.reverse,
                first_edition=row.first_edition,
            )
            # Riporto il prezzo di mercato sull'articolo: in inventario una
            # carta a zero euro sarebbe solo confondente.
            article.price = esito["price_eur"]
            db.commit()

            meta = esito.get("price_meta") or {}
            esiti.append(RowOutcome(
                index=i, ok=True,
                article_id=article.id,
                product_id=esito.get("product_id"),
                price_eur=esito.get("price_eur"),
                price_position=meta.get("position"),
                price_total_offers=meta.get("total"),
            ))
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            # L'articolo in bozza resta: senza inserzione non serve a
            # niente, e in elenco sarebbe una riga fantasma da ripulire.
            if article is not None and article.id:
                try:
                    db.delete(article)
                    db.commit()
                except Exception:  # noqa: BLE001
                    db.rollback()
            LOGGER.warning("Riga %s non caricata (%s): %s", i, row.blueprint_id, exc)
            esiti.append(RowOutcome(index=i, ok=False, error=str(exc)))

    return esiti


# ── Ingresso da CSV ────────────────────────────────────────────────

# Intestazioni accettate, in italiano e in inglese: un file esportato da
# un altro gestionale non deve essere rinominato a mano per entrare.
COLONNE = {
    "nome": "name", "carta": "name", "name": "name", "card": "name",
    "numero": "number", "number": "number", "collector_number": "number",
    "espansione": "collection", "set": "collection", "collezione": "collection",
    "expansion": "collection", "collection": "collection",
    "quantita": "quantity", "quantità": "quantity", "qta": "quantity",
    "qty": "quantity", "quantity": "quantity",
    "condizione": "condition", "condition": "condition",
    "lingua": "language", "language": "language",
    "reverse": "reverse", "foil": "reverse",
    "prima_edizione": "first_edition", "prima edizione": "first_edition",
    "first_edition": "first_edition", "1st": "first_edition",
}

VERO = {"1", "si", "sì", "true", "vero", "x", "yes", "y"}


class CsvRequest(BaseModel):
    csv_text: str = Field(..., min_length=1, max_length=200_000)
    # Se tutte le carte vengono dallo stesso set, dirlo rende la
    # risoluzione esatta invece che euristica.
    expansion_id: Optional[int] = None
    game_id: Optional[int] = None


class CsvRow(BaseModel):
    index: int
    name: Optional[str] = None
    number: Optional[str] = None
    collection: Optional[str] = None
    quantity: int = 1
    condition: str = "Near Mint"
    language: Optional[str] = None
    reverse: bool = False
    first_edition: bool = False
    candidates: List[Dict[str, Any]] = []
    error: Optional[str] = None


def _sniff(testo: str) -> str:
    """Virgola o punto e virgola: i CSV italiani usano quasi sempre il
    secondo, perche' Excel con la virgola decimale non puo' fare altro."""
    prima = testo.splitlines()[0] if testo.splitlines() else ""
    return ";" if prima.count(";") > prima.count(",") else ","


@router.post("/parse-csv", response_model=List[CsvRow])
def parse_csv(
    payload: CsvRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Legge il CSV e, per ogni riga, propone i blueprint possibili.

    Non pubblica niente: i candidati li conferma una persona. Un nome che
    somiglia non e' un nome che coincide, e una carta sbagliata messa in
    vendita la si scopre quando qualcuno l'ha comprata.
    """
    _guard()
    testo = payload.csv_text.strip()
    if not testo:
        raise HTTPException(400, "File vuoto")

    lettore = csv.DictReader(io.StringIO(testo), delimiter=_sniff(testo))
    if not lettore.fieldnames:
        raise HTTPException(400, "Manca la riga di intestazione")

    mappa = {}
    for col in lettore.fieldnames:
        chiave = COLONNE.get((col or "").strip().lower())
        if chiave:
            mappa[col] = chiave
    if "name" not in mappa.values() and "number" not in mappa.values():
        raise HTTPException(
            400,
            "Serve almeno una colonna con il nome o il numero della carta "
            f"(intestazioni lette: {', '.join(lettore.fieldnames)})",
        )

    game_id = payload.game_id or cts._default_game_id(db)
    righe: List[CsvRow] = []

    for i, grezza in enumerate(lettore):
        if i >= MAX_RIGHE:
            break
        valori: Dict[str, Any] = {}
        for col, chiave in mappa.items():
            valori[chiave] = (grezza.get(col) or "").strip()

        riga = CsvRow(
            index=i,
            name=valori.get("name") or None,
            number=valori.get("number") or None,
            collection=valori.get("collection") or None,
            quantity=int(valori["quantity"]) if valori.get("quantity", "").isdigit() else 1,
            condition=valori.get("condition") or "Near Mint",
            language=valori.get("language") or None,
            reverse=valori.get("reverse", "").lower() in VERO,
            first_edition=valori.get("first_edition", "").lower() in VERO,
        )
        if not (riga.name or riga.number):
            riga.error = "Riga senza nome né numero"
            righe.append(riga)
            continue

        try:
            if payload.expansion_id:
                # Espansione nota: il numero identifica la carta senza
                # tirare a indovinare sul nome.
                tutti = ct.blueprints_cached(payload.expansion_id)
                riga.candidates = _filtra_blueprint(tutti, riga.name, riga.number)[:5]
            else:
                riga.candidates = cts.resolve_blueprints(
                    riga.collection, riga.number, riga.name, game_id
                )[:5]
        except ct.CardTraderError as exc:
            riga.error = str(exc)
        righe.append(riga)

    return righe


def _filtra_blueprint(
    blueprints: List[dict], name: Optional[str], number: Optional[str],
) -> List[dict]:
    """Dentro un'espansione nota: prima il numero (che e' univoco), poi il
    nome come ripiego."""
    if number:
        n = str(number).strip().lstrip("0").lower()
        esatti = [
            b for b in blueprints
            if str(b.get("collector_number", "")).strip().lstrip("0").lower() == n
        ]
        if esatti:
            return esatti
    if name:
        q = name.strip().lower()
        return [b for b in blueprints if q in str(b.get("name", "")).lower()]
    return []
