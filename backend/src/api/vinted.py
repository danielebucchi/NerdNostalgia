"""
API endpoint sync Vinted (admin only):
  GET   /api/vinted/settings    → config attuale
  PATCH /api/vinted/settings    → modifica config (user_id, sync_hour, enabled)
  GET   /api/vinted/logs        → ultime sync
  POST  /api/vinted/sync        → trigger manuale (sincrono)
  POST  /api/vinted/import      → import di items fetchati altrove
  POST  /api/vinted/reconcile   → archivia gli item spariti da Vinted
"""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from models.db import User, VintedSettings, VintedSyncLog
from utils.session import get_db
from utils.vinted_client import VintedItem
from utils.vinted_sync import (
    archive_missing_items,
    persist_items,
    reconcile_candidates,
    run_sync,
)

router = APIRouter(prefix="/api/vinted", tags=["vinted"])

LOGGER = logging.getLogger("vinted_api")


# ----------------------------- Schemas Pydantic -----------------------------
class VintedSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vinted_user_id: int
    enabled: bool
    sync_hour: int
    last_run_at: Optional[datetime]


class VintedSettingsUpdate(BaseModel):
    vinted_user_id: Optional[int] = Field(None, ge=1)
    enabled: Optional[bool] = None
    sync_hour: Optional[int] = Field(None, ge=0, le=23)


class VintedSyncLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    started_at: datetime
    finished_at: Optional[datetime]
    triggered_by: str
    items_fetched: int
    items_imported: int
    items_updated: int
    items_skipped: int
    items_archived: int = 0
    error_message: Optional[str]


class VintedItemPayload(BaseModel):
    """Singolo item nel body di POST /api/vinted/import. Specchio
    minimale di utils.vinted_client.VintedItem (escluso `raw`)."""
    item_id: int = Field(..., ge=1)
    title: str
    description: Optional[str] = None
    price: Optional[float] = None
    currency: str = "EUR"
    url: str
    photos: List[str] = Field(default_factory=list)
    catalog_id: Optional[int] = None
    catalog_branch_title: Optional[str] = None
    status: Optional[str] = None


class VintedImportRequest(BaseModel):
    items: List[VintedItemPayload]
    triggered_by: str = Field(default="remote", max_length=20)
    seen_item_ids: Optional[List[int]] = Field(
        default=None,
        description=(
            "Tutti gli item_id visti sul profilo in questa run, PRIMA di "
            "qualunque filtro lato client. Se presente, la risposta include "
            "i candidati alla riconciliazione. Ometterlo disattiva il giro."
        ),
    )


class VintedImportResponse(VintedSyncLogResponse):
    """Log dell'import + esito del calcolo dei candidati alla rimozione."""
    reconcile_candidates: List[int] = Field(default_factory=list)
    reconcile_skipped_reason: Optional[str] = None


class VintedReconcileRequest(BaseModel):
    missing_item_ids: List[int] = Field(
        ...,
        description=(
            "item_id verificati come spariti (404/410 su /items/{id}) dal "
            "client, che deve girare su IP residenziale."
        ),
    )
    triggered_by: str = Field(default="reconcile", max_length=20)


# ----------------------------- Settings -----------------------------
def _get_or_404(db: Session) -> VintedSettings:
    s = db.query(VintedSettings).order_by(VintedSettings.id.asc()).first()
    if not s:
        raise HTTPException(404, "Vinted settings non configurate")
    return s


@router.get("/settings", response_model=VintedSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return _get_or_404(db)


@router.patch("/settings", response_model=VintedSettingsResponse)
def update_settings(
    payload: VintedSettingsUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    s = _get_or_404(db)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s


# ----------------------------- Logs -----------------------------
@router.get("/logs", response_model=List[VintedSyncLogResponse])
def list_logs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return (
        db.query(VintedSyncLog)
        .order_by(VintedSyncLog.started_at.desc())
        .limit(limit)
        .all()
    )


# ----------------------------- Sync trigger -----------------------------
@router.post("/sync", response_model=VintedSyncLogResponse)
def trigger_sync(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Trigger sync manuale (sincrono — l'admin vede l'esito immediato).

    Esegue il fetch via Playwright sul server. Se il server è su un IP
    datacenter dove Cloudflare blocca lo headless browser, vedi invece
    `POST /api/vinted/import` + lo script `backend/scripts/sync_from_local.py`
    che fa il fetch dal Mac (IP residenziale) e poi pusha qui.
    """
    log = run_sync(db, triggered_by="manual")
    return log


@router.post("/import", response_model=VintedImportResponse)
def import_items(
    payload: VintedImportRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Import di items già fetchati altrove (es. dal Mac dell'admin, IP
    residenziale, dove Cloudflare non blocca Playwright).

    Body atteso:
        {
          "items": [ {item_id, title, price, photos: [...], ...}, ... ],
          "triggered_by": "remote"   # opzionale, tag per i logs
        }

    Le foto vengono scaricate dal CDN Vinted lato server (no CF su CDN).
    """
    items = [
        VintedItem(
            item_id=p.item_id,
            title=p.title,
            description=p.description,
            price=p.price,
            currency=p.currency,
            url=p.url,
            photos=p.photos,
            catalog_id=p.catalog_id,
            catalog_branch_title=p.catalog_branch_title,
            status=p.status,
            raw={},  # non trasportato dal client per ridurre payload
        )
        for p in payload.items
    ]
    log = persist_items(db, items, triggered_by=payload.triggered_by)

    candidates: List[int] = []
    skipped_reason: Optional[str] = None
    if payload.seen_item_ids is not None:
        candidates, skipped_reason = reconcile_candidates(
            db, payload.seen_item_ids, exclude_log_id=log.id,
        )
        if skipped_reason:
            LOGGER.info("Riconciliazione saltata: %s", skipped_reason)

    return VintedImportResponse(
        **VintedSyncLogResponse.model_validate(log).model_dump(),
        reconcile_candidates=candidates,
        reconcile_skipped_reason=skipped_reason,
    )


@router.post("/reconcile", response_model=VintedSyncLogResponse)
def reconcile(
    payload: VintedReconcileRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Archivia gli articoli i cui item sono spariti da Vinted.

    Secondo tempo del giro avviato da `POST /api/vinted/import`: il client
    riceve `reconcile_candidates`, li verifica uno a uno con
    `verify_items_missing()` (404/410 su /items/{id}) e rimanda qui solo
    quelli confermati.

    Gli articoli passano a `ARCHIVED`: spariscono dal catalogo pubblico e
    dagli ordinabili, ma foto e storico restano. Il server rivalida ogni ID
    contro l'ultimo import e rifiuta quelli toccati di recente.
    """
    return archive_missing_items(
        db, payload.missing_item_ids, triggered_by=payload.triggered_by,
    )
