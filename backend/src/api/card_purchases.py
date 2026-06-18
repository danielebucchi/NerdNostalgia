"""
API endpoint per le spese carte all'ingrosso.
"""
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from helpers.auth import require_admin
from helpers.card_purchase import CardPurchaseHelper, get_card_purchase_helper
from models.db import CardPurchase, User
from models.entities.card_purchase import (
    CardPurchaseCreate,
    CardPurchaseListResponse,
    CardPurchaseResponse,
    CardPurchaseUpdate,
)

router = APIRouter(prefix="/api/card-purchases", tags=["card-purchases"])


def _to_response(item: CardPurchase) -> CardPurchaseResponse:
    return CardPurchaseResponse(
        id=item.id,
        purchase_date=item.purchase_date,
        item=item.item,
        amount=item.amount,
        note=item.note,
        created_at=item.created_at.isoformat() if item.created_at else None,
        updated_at=item.updated_at.isoformat() if item.updated_at else None,
    )


@router.get("/", response_model=CardPurchaseListResponse)
def list_purchases(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    helper: CardPurchaseHelper = Depends(get_card_purchase_helper),
    _admin: User = Depends(require_admin),
):
    items = helper.gets(year=year)
    total_amount = sum((i.amount or Decimal("0") for i in items), Decimal("0"))
    return CardPurchaseListResponse(
        items=[_to_response(i) for i in items],
        total=len(items),
        total_amount=total_amount,
    )


@router.post("/", response_model=CardPurchaseResponse, status_code=status.HTTP_201_CREATED)
def create_purchase(
    payload: CardPurchaseCreate,
    helper: CardPurchaseHelper = Depends(get_card_purchase_helper),
    _admin: User = Depends(require_admin),
):
    item = CardPurchase(
        purchase_date=payload.purchase_date,
        item=payload.item.strip(),
        amount=payload.amount,
        note=payload.note.strip() if payload.note else None,
    )
    helper.save(item)
    return _to_response(item)


@router.patch("/{item_id}", response_model=CardPurchaseResponse)
def update_purchase(
    item_id: int,
    payload: CardPurchaseUpdate,
    helper: CardPurchaseHelper = Depends(get_card_purchase_helper),
    _admin: User = Depends(require_admin),
):
    item = helper.get(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spesa {item_id} non trovata",
        )
    helper.update(payload, item)
    return _to_response(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase(
    item_id: int,
    helper: CardPurchaseHelper = Depends(get_card_purchase_helper),
    _admin: User = Depends(require_admin),
):
    item = helper.get(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spesa {item_id} non trovata",
        )
    helper.delete(item)
    return None
