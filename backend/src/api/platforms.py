"""API endpoint platforms. Read pubblico, write admin only."""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from helpers.auth import require_admin
from helpers.platform import PlatformHelper, get_platform_helper
from models.db import Platform, User
from models.entities.platform import (
    PlatformCreate,
    PlatformListResponse,
    PlatformResponse,
    PlatformUpdate,
)

router = APIRouter(prefix="/api/platforms", tags=["platforms"])


def _to_response(p: Platform) -> PlatformResponse:
    return PlatformResponse(
        id=p.id,
        name=p.name,
        slug=p.slug,
        icon=p.icon,
        display_order=p.display_order,
        is_active=p.is_active,
        note=p.note,
        created_at=p.created_at.isoformat() if p.created_at else "",
        updated_at=p.updated_at.isoformat() if p.updated_at else "",
    )


@router.get("/", response_model=PlatformListResponse)
def list_platforms(
    active_only: bool = Query(False),
    helper: PlatformHelper = Depends(get_platform_helper),
):
    items = helper.gets(active_only=active_only)
    return PlatformListResponse(
        items=[_to_response(p) for p in items],
        total=len(items),
    )


@router.post("/", response_model=PlatformResponse, status_code=status.HTTP_201_CREATED)
def create_platform(
    payload: PlatformCreate,
    helper: PlatformHelper = Depends(get_platform_helper),
    _admin: User = Depends(require_admin),
):
    if payload.slug and helper.get_by_slug(payload.slug):
        raise HTTPException(409, f"Slug '{payload.slug}' già esistente")
    platform = Platform(**payload.model_dump())
    platform.name = platform.name.strip()
    helper.save(platform)
    return _to_response(platform)


@router.patch("/{platform_id}", response_model=PlatformResponse)
def update_platform(
    platform_id: int,
    payload: PlatformUpdate,
    helper: PlatformHelper = Depends(get_platform_helper),
    _admin: User = Depends(require_admin),
):
    platform = helper.get(platform_id)
    if not platform:
        raise HTTPException(404, f"Platform {platform_id} non trovata")
    if payload.slug and payload.slug != platform.slug:
        other = helper.get_by_slug(payload.slug)
        if other and other.id != platform.id:
            raise HTTPException(409, f"Slug '{payload.slug}' già usato")
    helper.update(payload, platform)
    return _to_response(platform)


@router.delete("/{platform_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_platform(
    platform_id: int,
    helper: PlatformHelper = Depends(get_platform_helper),
    _admin: User = Depends(require_admin),
):
    platform = helper.get(platform_id)
    if not platform:
        raise HTTPException(404, f"Platform {platform_id} non trovata")
    helper.delete(platform)
    return None
