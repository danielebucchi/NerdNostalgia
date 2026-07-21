"""
API admin per CardTrader (Fase 1: connessione + catalogo + prezzo).

Tutti admin-only. Fanno da proxy verso CardTrader cosi' il JWT resta
lato server e il frontend non lo vede mai.
"""
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from helpers.article import ArticleHelper, get_article_helper
from helpers.auth import require_admin
from models.db import User
from utils import cardtrader_client as ct
from utils import cardtrader_sync as cts
from utils.session import get_db

router = APIRouter(prefix="/api/cardtrader", tags=["cardtrader"])


def _extract_product_id(resp: Any) -> Optional[int]:
    """Estrae l'id prodotto dalla risposta di POST /products, tollerando
    le forme note ({resource:{id}}, {id}, [{id}])."""
    if isinstance(resp, dict):
        if isinstance(resp.get("resource"), dict) and "id" in resp["resource"]:
            return resp["resource"]["id"]
        if "id" in resp:
            return resp["id"]
    if isinstance(resp, list) and resp and isinstance(resp[0], dict):
        return resp[0].get("id")
    return None


def _guard():
    if not ct.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CardTrader non configurato: manca CARDTRADER_JWT.",
        )


def _wrap(fn, *args, **kwargs) -> Any:
    _guard()
    try:
        return fn(*args, **kwargs)
    except ct.CardTraderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{exc} (body={exc.body})" if exc.body else str(exc),
        ) from exc


@router.get("/status")
def status_check(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Prova connessione: token valido + server raggiunge l'API.
    Include il gioco predefinito (per la dropdown espansioni del box)."""
    default_game = cts._default_game_id(db)
    if not ct.is_configured():
        return {"configured": False, "ok": False, "detail": "CARDTRADER_JWT mancante",
                "default_game_id": default_game}
    try:
        info = ct.info()
        return {"configured": True, "ok": True, "info": info,
                "default_game_id": default_game}
    except ct.CardTraderError as exc:
        return {
            "configured": True,
            "ok": False,
            "status": exc.status,
            "detail": str(exc),
            "body": exc.body,
            "default_game_id": default_game,
        }


@router.get("/games")
def list_games(_admin: User = Depends(require_admin)):
    return _wrap(ct.games)


@router.get("/expansions")
def list_expansions(
    game_id: Optional[int] = Query(None, description="Filtra per gioco"),
    search: Optional[str] = Query(None, description="Cerca per nome o codice"),
    limit: int = Query(300, ge=1, le=5000),
    _admin: User = Depends(require_admin),
):
    """Elenco espansioni CardTrader (la lista ufficiale delle 'collezioni').
    Con game_id/search per scegliere quella esatta senza digitarla a mano.
    Arricchito col nome del gioco per contesto."""
    _guard()
    try:
        exps = ct.expansions_cached()
        game_names = {g["id"]: g.get("display_name") or g.get("name") for g in ct.games()}
    except ct.CardTraderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    if game_id is not None:
        exps = [e for e in exps if e.get("game_id") == game_id]
    if search:
        q = search.lower()
        exps = [
            e for e in exps
            if q in str(e.get("name", "")).lower() or q in str(e.get("code", "")).lower()
        ]
    exps = sorted(exps, key=lambda e: str(e.get("name", "")))[:limit]
    return [
        {**e, "game_name": game_names.get(e.get("game_id"))}
        for e in exps
    ]


@router.get("/blueprints")
def list_blueprints(
    expansion_id: int = Query(..., description="ID espansione CardTrader"),
    search: Optional[str] = Query(None, description="Filtra per nome/numero carta"),
    _admin: User = Depends(require_admin),
):
    items = _wrap(ct.blueprints, expansion_id)
    if search:
        q = search.lower()
        items = [
            b for b in items
            if q in str(b.get("name", "")).lower()
            or q in str(b.get("collector_number", "")).lower()
        ]
    return items[:200]


@router.get("/resolve")
def resolve_blueprint(
    collection: Optional[str] = Query(None, description="Collezione/espansione (testo libero)"),
    number: Optional[str] = Query(None, description="Numero carta"),
    name: Optional[str] = Query(None, description="Nome carta (bonus match)"),
    game_id: Optional[int] = Query(None),
    article_id: Optional[int] = Query(None, description="Se passato, usa i campi carta dell'articolo"),
    helper: ArticleHelper = Depends(get_article_helper),
    _admin: User = Depends(require_admin),
):
    """Candidati blueprint da collezione+numero (+nome). Match espansione
    euristico → si confermano i candidati, non si assegna in automatico."""
    _guard()
    if article_id is not None:
        art = helper.get("id", article_id)
        if art:
            collection = collection or art.card_collection
            number = number or art.card_number
            name = name or art.title
    if game_id is None:
        game_id = cts._default_game_id(helper.db)
    if not (collection or number or name):
        raise HTTPException(400, "Fornisci almeno collezione, numero o nome")
    try:
        cands = cts.resolve_blueprints(collection, number, name, game_id)
    except ct.CardTraderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return {"game_id": game_id, "candidates": cands}


@router.get("/suggested-price")
def suggested_price(
    blueprint_id: int = Query(...),
    position: int = Query(4, ge=1, le=50, description="N-esimo piu' basso (default 4°)"),
    condition: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    reverse: Optional[bool] = Query(None),
    first_edition: Optional[bool] = Query(None),
    _admin: User = Depends(require_admin),
):
    """4° prezzo piu' basso, filtrato per condizione/lingua/reverse/prima
    edizione se passati (comparabili con la carta che vendi)."""
    res = _wrap(
        ct.suggested_price_cents, blueprint_id, position,
        condition=condition, language=language,
        reverse=reverse, first_edition=first_edition,
    )
    if res is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nessuna inserzione con prezzo per questi filtri",
        )
    res["eur"] = round(res["cents"] / 100, 2)
    return res


# ── Pubblicazione articolo → prodotto CardTrader ───────────────────

class PublishRequest(BaseModel):
    # Prezzo: se assente, calcolato come N-esimo piu' basso dal marketplace
    # (filtrato per condizione/lingua/reverse/prima edizione)
    price_eur: Optional[float] = Field(None, ge=0)
    price_position: int = Field(4, ge=1, le=50, description="N-esimo piu' basso (default 4°)")
    quantity: Optional[int] = Field(None, ge=1)
    condition: str = Field("Near Mint")
    language: Optional[str] = Field(None, description="Codice lingua CardTrader (it/en/...)")
    reverse: Optional[bool] = None
    first_edition: Optional[bool] = None


@router.post("/publish/{article_id}")
def publish_article(
    article_id: int,
    payload: PublishRequest,
    db: Session = Depends(get_db),
    helper: ArticleHelper = Depends(get_article_helper),
    _admin: User = Depends(require_admin),
):
    """Mette in vendita l'articolo su CardTrader. Serve
    cardtrader_blueprint_id gia' abbinato. Prezzo = 4° piu' basso se non
    passato esplicitamente. Se gia' pubblicato, aggiorna prezzo/quantita'."""
    _guard()
    article = helper.get("id", article_id)
    if not article:
        raise HTTPException(404, f"Articolo {article_id} non trovato")
    # Persisti gli attributi scelti sull'articolo (così restano coerenti col
    # prezzo mostrato e con eventuali repubblicazioni / la scheda sul sito).
    article.card_condition = payload.condition
    if payload.language is not None:
        article.card_language = payload.language
    if payload.reverse is not None:
        article.card_reverse = payload.reverse
    if payload.first_edition is not None:
        article.card_first_edition = payload.first_edition
    db.commit()
    try:
        return cts.publish_article(
            db, article,
            price_eur=payload.price_eur,
            price_position=payload.price_position,
            quantity=payload.quantity,
            condition=payload.condition,
            language=payload.language,
            reverse=payload.reverse,
            first_edition=payload.first_edition,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ct.CardTraderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{exc} (body={exc.body})" if exc.body else str(exc),
        ) from exc


@router.post("/unpublish/{article_id}")
def unpublish_article(
    article_id: int,
    db: Session = Depends(get_db),
    helper: ArticleHelper = Depends(get_article_helper),
    _admin: User = Depends(require_admin),
):
    """Rimuove il prodotto da CardTrader (l'abbinamento blueprint resta)."""
    _guard()
    article = helper.get("id", article_id)
    if not article:
        raise HTTPException(404, f"Articolo {article_id} non trovato")
    if not article.cardtrader_product_id:
        raise HTTPException(400, "Articolo non pubblicato su CardTrader")
    try:
        cts.unpublish_article(db, article)
    except ct.CardTraderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return {"ok": True}
