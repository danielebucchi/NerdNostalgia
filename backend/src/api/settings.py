"""
API settings runtime.

GET /api/settings/public   — pubblico, solo chiavi con public=True (il
                             frontend le legge a runtime, niente rebuild).
GET /api/settings/         — admin, tutte le chiavi con label/help per la UI.
PUT /api/settings/         — admin, upsert batch {key: value}.
"""
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from helpers.auth import require_admin
from helpers.setting import SETTINGS_SPEC, SettingHelper, get_setting_helper
from models.db import Setting, User

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingEntry(BaseModel):
    key: str
    value: str            # valore salvato nel DB ("" = usa default/fallback)
    effective: str        # valore effettivo (DB o default SPEC)
    default: str
    public: bool
    label: str
    help: Optional[str] = None


class SettingsUpdateRequest(BaseModel):
    values: Dict[str, str] = Field(..., description="Mappa {key: value} da salvare")


@router.get("/public", response_model=Dict[str, str])
def get_public_settings(helper: SettingHelper = Depends(get_setting_helper)):
    """Chiavi pubbliche con valore effettivo. Nessuna auth."""
    return helper.get_effective(public_only=True)


@router.get("/", response_model=List[SettingEntry])
def list_settings(
    helper: SettingHelper = Depends(get_setting_helper),
    _admin: User = Depends(require_admin),
):
    stored = {s.key: s.value for s in helper.db.query(Setting).all()}
    out: List[SettingEntry] = []
    for key, spec in SETTINGS_SPEC.items():
        value = stored.get(key, "")
        out.append(SettingEntry(
            key=key,
            value=value,
            effective=value if value != "" else spec["default"],
            default=spec["default"],
            public=spec["public"],
            label=spec["label"],
            help=spec.get("help"),
        ))
    return out


@router.put("/", response_model=List[SettingEntry])
def update_settings(
    payload: SettingsUpdateRequest,
    helper: SettingHelper = Depends(get_setting_helper),
    admin: User = Depends(require_admin),
):
    unknown = [k for k in payload.values if k not in SETTINGS_SPEC]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chiavi sconosciute: {', '.join(sorted(unknown))}",
        )
    for key, value in payload.values.items():
        helper.upsert(key, value)
    return list_settings(helper=helper, _admin=admin)
