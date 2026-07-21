"""
API admin per CardTrader (Fase 1: connessione + catalogo + prezzo).

Tutti admin-only. Fanno da proxy verso CardTrader cosi' il JWT resta
lato server e il frontend non lo vede mai.
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from helpers.auth import require_admin
from models.db import User
from utils import cardtrader_client as ct

router = APIRouter(prefix="/api/cardtrader", tags=["cardtrader"])


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
