"""
API endpoint per la sezione cerco/compro.
"""
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from helpers.auth import require_admin
from helpers.wanted import WantedItemHelper, get_wanted_helper
from models.db import ArticleCondition, User, WantedItem, WantedStatus
from models.entities.wanted import (
    WantedItemCreate,
    WantedItemListResponse,
    WantedItemResponse,
    WantedItemUpdate,
)

router = APIRouter(prefix="/api/wanted", tags=["wanted"])


def _to_response(item: WantedItem) -> WantedItemResponse:
    return WantedItemResponse(
        id=item.id,
        title=item.title,
        description=item.description,
        category=item.category,
        brand=item.brand,
        model=item.model,
        preferred_condition=item.preferred_condition.value if item.preferred_condition else None,
        max_price=item.max_price,
        currency=item.currency,
        notes=item.notes,
        priority=item.priority,
        status=item.status.value,
        created_at=item.created_at.isoformat() if item.created_at else None,
        updated_at=item.updated_at.isoformat() if item.updated_at else None,
        fulfilled_at=item.fulfilled_at.isoformat() if item.fulfilled_at else None,
    )


@router.get("/", response_model=WantedItemListResponse)
def list_wanted(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[WantedStatus] = Query(None, alias="status"),
    category: Optional[str] = None,
    condition: Optional[ArticleCondition] = None,
    max_budget: Optional[Decimal] = Query(None, ge=0),
    search: Optional[str] = None,
    helper: WantedItemHelper = Depends(get_wanted_helper),
):
    """Lista pubblica degli articoli cercati. Default: solo ACTIVE."""
    db_status = WantedStatus(status_filter.value) if status_filter else WantedStatus.ACTIVE
    db_condition = ArticleCondition(condition.value) if condition else None

    items, total = helper.gets(
        skip=skip,
        limit=limit,
        status=db_status,
        category=category,
        condition=db_condition,
        max_budget=max_budget,
        search=search,
    )
    return WantedItemListResponse(
        items=[_to_response(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{wanted_id}", response_model=WantedItemResponse)
def get_wanted(
    wanted_id: int,
    helper: WantedItemHelper = Depends(get_wanted_helper),
):
    """Dettaglio articolo cercato (pubblico)."""
    item = helper.get("id", wanted_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wanted con ID {wanted_id} non trovato",
        )
    return _to_response(item)


@router.post("/", response_model=WantedItemResponse, status_code=status.HTTP_201_CREATED)
def create_wanted(
    data: WantedItemCreate,
    helper: WantedItemHelper = Depends(get_wanted_helper),
    _admin: User = Depends(require_admin),
):
    """Crea un nuovo wanted (admin)."""
    new_item = WantedItem(
        title=data.title,
        description=data.description,
        category=data.category,
        brand=data.brand,
        model=data.model,
        preferred_condition=(
            ArticleCondition(data.preferred_condition.value)
            if data.preferred_condition
            else None
        ),
        max_price=data.max_price,
        currency=data.currency,
        notes=data.notes,
        priority=data.priority,
        status=WantedStatus(data.status.value),
    )
    helper.save(new_item)
    return _to_response(new_item)


@router.patch("/{wanted_id}", response_model=WantedItemResponse)
def update_wanted(
    wanted_id: int,
    data: WantedItemUpdate,
    helper: WantedItemHelper = Depends(get_wanted_helper),
    _admin: User = Depends(require_admin),
):
    """Aggiorna wanted (admin). Passando status=FULFILLED popola fulfilled_at."""
    item = helper.get("id", wanted_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wanted con ID {wanted_id} non trovato",
        )
    helper.update(data, item)
    return _to_response(item)


@router.delete("/{wanted_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wanted(
    wanted_id: int,
    helper: WantedItemHelper = Depends(get_wanted_helper),
    _admin: User = Depends(require_admin),
):
    """Elimina wanted (admin)."""
    item = helper.get("id", wanted_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wanted con ID {wanted_id} non trovato",
        )
    helper.delete(item)
    return None
