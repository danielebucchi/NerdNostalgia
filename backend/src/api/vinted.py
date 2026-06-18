"""
API endpoint sync Vinted (admin only):
  GET  /api/vinted/settings        → config attuale
  PATCH /api/vinted/settings       → modifica config
  GET  /api/vinted/mappings        → lista mapping
  POST /api/vinted/mappings        → crea mapping
  PATCH /api/vinted/mappings/{id}  → update mapping
  DELETE /api/vinted/mappings/{id} → elimina mapping
  GET  /api/vinted/logs            → ultime 20 sync
  POST /api/vinted/sync            → trigger manuale
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from models.db import (
    User,
    VintedCategoryMapping,
    VintedSettings,
    VintedSyncLog,
)
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


class VintedMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vinted_catalog_id: int
    vinted_catalog_name: str
    category_id: Optional[int]
    enabled: bool


class VintedMappingCreate(BaseModel):
    vinted_catalog_id: int = Field(..., ge=1)
    vinted_catalog_name: str = Field(..., min_length=1, max_length=200)
    category_id: Optional[int] = None
    enabled: bool = True


class VintedMappingUpdate(BaseModel):
    vinted_catalog_name: Optional[str] = Field(None, min_length=1, max_length=200)
    category_id: Optional[int] = None
    enabled: Optional[bool] = None


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


# ----------------------------- Mappings -----------------------------
@router.get("/mappings", response_model=List[VintedMappingResponse])
def list_mappings(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return (
        db.query(VintedCategoryMapping)
        .order_by(VintedCategoryMapping.vinted_catalog_id.asc())
        .all()
    )


@router.post(
    "/mappings",
    response_model=VintedMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_mapping(
    payload: VintedMappingCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    existing = (
        db.query(VintedCategoryMapping)
        .filter(VintedCategoryMapping.vinted_catalog_id == payload.vinted_catalog_id)
        .first()
    )
    if existing:
        raise HTTPException(
            400, f"catalog_id {payload.vinted_catalog_id} gia mappato"
        )
    m = VintedCategoryMapping(
        vinted_catalog_id=payload.vinted_catalog_id,
        vinted_catalog_name=payload.vinted_catalog_name.strip(),
        category_id=payload.category_id,
        enabled=payload.enabled,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.patch("/mappings/{mapping_id}", response_model=VintedMappingResponse)
def update_mapping(
    mapping_id: int,
    payload: VintedMappingUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    m = db.query(VintedCategoryMapping).get(mapping_id)
    if not m:
        raise HTTPException(404, f"Mapping {mapping_id} non trovato")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    m = db.query(VintedCategoryMapping).get(mapping_id)
    if not m:
        raise HTTPException(404, f"Mapping {mapping_id} non trovato")
    db.delete(m)
    db.commit()
    return None


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
    """Trigger sync manuale (sincrono per ora — l'admin vede l'esito).

    In futuro si puo' renderlo BackgroundTasks se i fetch diventano lunghi.
    """
    log = run_sync(db, triggered_by="manual")
    return log
