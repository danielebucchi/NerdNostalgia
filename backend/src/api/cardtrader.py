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
def status_check(_admin: User = Depends(require_admin)):
    """Prova connessione: token valido + server raggiunge l'API."""
    if not ct.is_configured():
        return {"configured": False, "ok": False, "detail": "CARDTRADER_JWT mancante"}
    try:
        info = ct.info()
        return {"configured": True, "ok": True, "info": info}
    except ct.CardTraderError as exc:
        return {
            "configured": True,
            "ok": False,
            "status": exc.status,
            "detail": str(exc),
            "body": exc.body,
        }


@router.get("/games")
def list_games(_admin: User = Depends(require_admin)):
    return _wrap(ct.games)


@router.get("/expansions")
def list_expansions(_admin: User = Depends(require_admin)):
    return _wrap(ct.expansions)


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


@router.get("/suggested-price")
def suggested_price(
    blueprint_id: int = Query(...),
    position: int = Query(4, ge=1, le=50, description="N-esimo piu' basso (default 4°)"),
    _admin: User = Depends(require_admin),
):
    res = _wrap(ct.suggested_price_cents, blueprint_id, position)
    if res is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nessuna inserzione con prezzo per questo blueprint",
        )
    res["eur"] = round(res["cents"] / 100, 2)
    return res


# ── Pubblicazione articolo → prodotto CardTrader ───────────────────

class PublishRequest(BaseModel):
    # Prezzo: se assente, calcolato come N-esimo piu' basso dal marketplace
    price_eur: Optional[float] = Field(None, ge=0)
    price_position: int = Field(4, ge=1, le=50, description="N-esimo piu' basso (default 4°)")
    quantity: Optional[int] = Field(None, ge=1)
    condition: str = Field("Near Mint")


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
    if not article.cardtrader_blueprint_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Articolo non abbinato a un blueprint CardTrader.",
        )

    # Prezzo
    price_eur = payload.price_eur
    price_meta = None
    if price_eur is None:
        sug = ct.suggested_price_cents(
            article.cardtrader_blueprint_id, payload.price_position
        )
        if not sug:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Nessuna inserzione di riferimento: imposta un prezzo manuale.",
            )
        price_eur = round(sug["cents"] / 100, 2)
        price_meta = sug

    qty = payload.quantity or article.quantity or 1
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    try:
        if article.cardtrader_product_id:
            # gia' pubblicato → aggiorno prezzo e quantita'
            ct.update_product(
                article.cardtrader_product_id,
                price=price_eur,
                quantity=qty,
            )
            product_id = article.cardtrader_product_id
            action = "updated"
        else:
            resp = ct.create_product(
                blueprint_id=article.cardtrader_blueprint_id,
                price_eur=price_eur,
                quantity=qty,
                condition=payload.condition,
            )
            product_id = _extract_product_id(resp)
            action = "created"
    except ct.CardTraderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{exc} (body={exc.body})" if exc.body else str(exc),
        ) from exc

    article.cardtrader_product_id = product_id
    article.cardtrader_synced_at = now
    db.commit()
    db.refresh(article)

    return {
        "action": action,
        "product_id": product_id,
        "price_eur": price_eur,
        "quantity": qty,
        "price_meta": price_meta,
    }


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
        ct.delete_product(article.cardtrader_product_id)
    except ct.CardTraderError as exc:
        # 404 CardTrader = gia' rimosso: procedo comunque a pulire da noi
        if exc.status != 404:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
            ) from exc
    article.cardtrader_product_id = None
    db.commit()
    return {"ok": True}
