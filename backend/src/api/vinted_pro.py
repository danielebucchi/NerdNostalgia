"""
API admin Vinted Pro (Fase 1: connessione/ispezione).

Router separato da /api/vinted (che è lo scraping legacy). La pubblicazione
degli articoli via VPI arriva in Fase 2, una volta ottenuto l'accesso
allowlist e verificato lo schema item/ontologie in sandbox.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from helpers.auth import require_admin
from models.db import User
from utils import vinted_pro_client as vp

router = APIRouter(prefix="/api/vinted-pro", tags=["vinted-pro"])


def _wrap(fn, *args, **kwargs) -> Any:
    if not vp.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vinted Pro non configurato: mancano access/signing key (portale VPI).",
        )
    try:
        return fn(*args, **kwargs)
    except vp.VintedProError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{exc} (body={exc.body})" if exc.body else str(exc),
        ) from exc


@router.get("/status")
def status_check(_admin: User = Depends(require_admin)):
    return {
        "env": "sandbox" if vp.is_sandbox() else "production",
        "configured": vp.is_configured(),
    }


@router.get("/ontologies")
def ontologies(_admin: User = Depends(require_admin)):
    """Tassonomia Vinted: serve a mappare le nostre categorie in Fase 2."""
    return _wrap(vp.get_ontologies)
