"""
API endpoint sync Vinted (admin only):
  GET   /api/vinted/settings    → config attuale
  PATCH /api/vinted/settings    → modifica config (user_id, sync_hour, enabled)
  GET   /api/vinted/logs        → ultime sync
  POST  /api/vinted/sync        → trigger manuale (sincrono)
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from models.db import User, VintedSettings, VintedSyncLog
from utils.session import get_db
from utils.vinted_sync import run_sync

router = APIRouter(prefix="/api/vinted", tags=["vinted"])


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
    error_message: Optional[str]


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
    """Trigger sync manuale (sincrono — l'admin vede l'esito immediato)."""
    log = run_sync(db, triggered_by="manual")
    return log
