"""
API admin eBay (Fase 1: connessione, consenso OAuth, ispezione account/taxonomy).

Tutto admin-only e proxy lato server: le credenziali/token eBay non arrivano
mai al browser. La pubblicazione vera e propria degli articoli arriva in
Fase 2, una volta completato il consenso e letta la taxonomy reale.
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from helpers.auth import require_admin
from models.db import User
from utils import ebay_client as eb

router = APIRouter(prefix="/api/ebay", tags=["ebay"])


def _wrap(fn, *args, **kwargs) -> Any:
    if not eb.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="eBay non configurato: manca il refresh token (completa il consenso).",
        )
    try:
        return fn(*args, **kwargs)
    except eb.EbayError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{exc} (body={exc.body})" if exc.body else str(exc),
        ) from exc


@router.get("/status")
def status_check(_admin: User = Depends(require_admin)):
    """Stato configurazione: ambiente, se le credenziali ci sono, se il
    consenso è stato completato (refresh token presente)."""
    return {
        "env": "sandbox" if eb.is_sandbox() else "production",
        "marketplace_id": eb.marketplace_id(),
        "has_credentials": bool(eb._client_id() and eb._client_secret()),
        "can_start_consent": eb.can_start_consent(),
        "configured": eb.is_configured(),
    }


@router.get("/consent-url")
def consent_url(_admin: User = Depends(require_admin)):
    """URL da aprire per autorizzare l'app col tuo account eBay."""
    if not eb.can_start_consent():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Config incompleta: servono EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_REDIRECT_RUNAME.",
        )
    return {"url": eb.consent_url()}


class OAuthExchangeRequest(BaseModel):
    code: str


@router.post("/oauth-exchange")
def oauth_exchange(payload: OAuthExchangeRequest, _admin: User = Depends(require_admin)):
    """Scambia il `code` del redirect per i token. Restituisce il
    refresh_token da salvare in EBAY_REFRESH_TOKEN (vault) — dopo di che
    l'integrazione è operativa."""
    try:
        data = eb.exchange_code(payload.code.strip())
    except eb.EbayError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return {
        "refresh_token": data.get("refresh_token"),
        "refresh_token_expires_in": data.get("refresh_token_expires_in"),
        "note": "Salva refresh_token in EBAY_REFRESH_TOKEN (vault) e riavvia il backend.",
    }


# ── Ispezione account/taxonomy (serve a preparare il mapping) ──────

@router.get("/policies")
def policies(_admin: User = Depends(require_admin)):
    """Business policy dell'account (pagamento/reso/spedizione) + location:
    servono gli ID per pubblicare. Da impostare in /impostazioni."""
    return {
        "fulfillment": _wrap(eb.fulfillment_policies),
        "payment": _wrap(eb.payment_policies),
        "return": _wrap(eb.return_policies),
        "locations": _wrap(eb.inventory_locations),
    }


@router.get("/category-tree-id")
def category_tree_id(_admin: User = Depends(require_admin)):
    return {"category_tree_id": _wrap(eb.default_category_tree_id)}


@router.get("/category-suggestions")
def category_suggestions(
    q: str = Query(..., description="Testo per suggerire la categoria eBay"),
    tree_id: Optional[str] = Query(None),
    _admin: User = Depends(require_admin),
):
    tid = tree_id or _wrap(eb.default_category_tree_id)
    return _wrap(eb.category_suggestions, tid, q)


@router.get("/item-aspects")
def item_aspects(
    category_id: str = Query(...),
    tree_id: Optional[str] = Query(None),
    _admin: User = Depends(require_admin),
):
    """Item specifics (obbligatori/consigliati) per una categoria: serve a
    costruire correttamente le inserzioni."""
    tid = tree_id or _wrap(eb.default_category_tree_id)
    return _wrap(eb.item_aspects_for_category, tid, category_id)
