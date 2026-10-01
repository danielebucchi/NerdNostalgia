"""
API suggerimenti indirizzo (proxy verso Geoapify).

Pubblica e senza auth perche' serve al form di checkout di un compratore
anonimo. Due accorgimenti per non farne un rubinetto aperto sulla nostra
quota: rate-limit per IP e query minima di 3 caratteri.

NB: NIENTE `from __future__ import annotations` (vedi api/orders.py).
"""
import logging

from fastapi import APIRouter, Query, Request

from utils import address_autocomplete as aa
from utils.limiter import limiter

LOGGER = logging.getLogger("address_api")

router = APIRouter(prefix="/api/address", tags=["address"])


@router.get("/autocomplete")
@limiter.limit("20/minute;300/hour")
def autocomplete(
    request: Request,
    q: str = Query(..., min_length=3, max_length=120),
):
    """Suggerimenti per il campo indirizzo.

    `configured: false` dice al frontend di non mostrare il menu a tendina e
    di lasciare il campo come testo libero.
    """
    return {
        "configured": aa.is_configured(),
        "suggestions": aa.suggest(q),
    }
