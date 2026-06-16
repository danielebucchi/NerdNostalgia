"""
API endpoint per i markup di marketplace.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from helpers.auth import require_admin
from helpers.marketplace_fee import MarketplaceFeeHelper, get_marketplace_fee_helper
from models.db import MarketplaceFee, User
from models.entities.marketplace_fee import (
    MarketplaceFeeCreate,
    MarketplaceFeeListResponse,
    MarketplaceFeeResponse,
    MarketplaceFeeUpdate,
)

router = APIRouter(prefix="/api/marketplace-fees", tags=["marketplace-fees"])


def _to_response(fee: MarketplaceFee) -> MarketplaceFeeResponse:
    return MarketplaceFeeResponse(
        id=fee.id,
        marketplace=fee.marketplace,
        category=fee.category,
        markup_percent=fee.markup_percent,
        note=fee.note,
        created_at=fee.created_at.isoformat() if fee.created_at else None,
        updated_at=fee.updated_at.isoformat() if fee.updated_at else None,
    )


@router.get("/", response_model=MarketplaceFeeListResponse)
def list_fees(
    marketplace: Optional[str] = Query(None),
    helper: MarketplaceFeeHelper = Depends(get_marketplace_fee_helper),
):
    """Lista dei markup. Pubblico (serve al frontend per costruire i preset)."""
    fees = helper.gets(marketplace=marketplace)
    return MarketplaceFeeListResponse(
        items=[_to_response(f) for f in fees],
        total=len(fees),
    )


@router.post("/", response_model=MarketplaceFeeResponse, status_code=status.HTTP_201_CREATED)
def create_fee(
    payload: MarketplaceFeeCreate,
    helper: MarketplaceFeeHelper = Depends(get_marketplace_fee_helper),
    _admin: User = Depends(require_admin),
):
    """Crea un nuovo markup (admin)."""
    fee = MarketplaceFee(
        marketplace=payload.marketplace.strip().lower(),
        category=payload.category.strip() if payload.category else None,
        markup_percent=payload.markup_percent,
        note=payload.note.strip() if payload.note else None,
    )
    helper.save(fee)
    return _to_response(fee)


@router.patch("/{fee_id}", response_model=MarketplaceFeeResponse)
def update_fee(
    fee_id: int,
    payload: MarketplaceFeeUpdate,
    helper: MarketplaceFeeHelper = Depends(get_marketplace_fee_helper),
    _admin: User = Depends(require_admin),
):
    """Aggiorna un markup (admin)."""
    fee = helper.get(fee_id)
    if not fee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Markup con ID {fee_id} non trovato",
        )
    helper.update(payload, fee)
    return _to_response(fee)


@router.delete("/{fee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fee(
    fee_id: int,
    helper: MarketplaceFeeHelper = Depends(get_marketplace_fee_helper),
    _admin: User = Depends(require_admin),
):
    """Elimina un markup (admin)."""
    fee = helper.get(fee_id)
    if not fee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Markup con ID {fee_id} non trovato",
        )
    helper.delete(fee)
    return None
