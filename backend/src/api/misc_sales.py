"""
API endpoint per le vendite generiche.
"""
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from helpers.auth import require_admin
from helpers.misc_sale import MiscSaleHelper, get_misc_sale_helper
from models.db import MiscSale, User
from models.entities.misc_sale import (
    MiscSaleCreate,
    MiscSaleListResponse,
    MiscSaleResponse,
    MiscSaleUpdate,
)

router = APIRouter(prefix="/api/misc-sales", tags=["misc-sales"])


def _to_response(item: MiscSale) -> MiscSaleResponse:
    return MiscSaleResponse(
        id=item.id,
        sale_date=item.sale_date,
        item=item.item,
        amount=item.amount,
        seller=item.seller,
        platform=item.platform,
        paid_by_buyer=item.paid_by_buyer,
        note=item.note,
        created_at=item.created_at.isoformat() if item.created_at else None,
        updated_at=item.updated_at.isoformat() if item.updated_at else None,
    )


@router.get("/", response_model=MiscSaleListResponse)
def list_sales(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    seller: Optional[str] = None,
    helper: MiscSaleHelper = Depends(get_misc_sale_helper),
    _admin: User = Depends(require_admin),
):
    items = helper.gets(year=year, seller=seller)
    total_amount = Decimal("0")
    total_paid = Decimal("0")
    total_unpaid = Decimal("0")
    for s in items:
        amt = s.amount or Decimal("0")
        total_amount += amt
        if s.paid_by_buyer:
            total_paid += amt
        else:
            total_unpaid += amt
    return MiscSaleListResponse(
        items=[_to_response(i) for i in items],
        total=len(items),
        total_amount=total_amount,
        total_paid=total_paid,
        total_unpaid=total_unpaid,
    )


@router.post("/", response_model=MiscSaleResponse, status_code=status.HTTP_201_CREATED)
def create_sale(
    payload: MiscSaleCreate,
    helper: MiscSaleHelper = Depends(get_misc_sale_helper),
    _admin: User = Depends(require_admin),
):
    item = MiscSale(
        sale_date=payload.sale_date,
        item=payload.item.strip(),
        amount=payload.amount,
        seller=payload.seller.strip() if payload.seller else None,
        platform=payload.platform.strip() if payload.platform else None,
        paid_by_buyer=payload.paid_by_buyer,
        note=payload.note.strip() if payload.note else None,
    )
    helper.save(item)
    return _to_response(item)


@router.patch("/{item_id}", response_model=MiscSaleResponse)
def update_sale(
    item_id: int,
    payload: MiscSaleUpdate,
    helper: MiscSaleHelper = Depends(get_misc_sale_helper),
    _admin: User = Depends(require_admin),
):
    item = helper.get(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendita {item_id} non trovata",
        )
    helper.update(payload, item)
    return _to_response(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sale(
    item_id: int,
    helper: MiscSaleHelper = Depends(get_misc_sale_helper),
    _admin: User = Depends(require_admin),
):
    item = helper.get(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendita {item_id} non trovata",
        )
    helper.delete(item)
    return None
