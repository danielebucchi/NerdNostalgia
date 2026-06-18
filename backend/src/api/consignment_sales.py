"""API endpoint ConsignmentSale (contovendita). Admin only."""
from collections import defaultdict
from datetime import date as _date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from helpers.auth import require_admin
from helpers.consignment_sale import ConsignmentSaleHelper, get_consignment_sale_helper
from models.db import ConsignmentSale, User
from models.entities.consignment_sale import (
    ConsignmentListResponse,
    ConsignmentSaleCreate,
    ConsignmentSaleResponse,
    ConsignmentSaleUpdate,
    ConsignorBreakdown,
    MarkPaidRequest,
)

router = APIRouter(prefix="/api/consignment-sales", tags=["consignment-sales"])


def _commission_effective(s: ConsignmentSale) -> Decimal:
    """commission_amount esplicito vince; altrimenti calcola da %."""
    if s.commission_amount is not None:
        return s.commission_amount
    if s.commission_pct is not None and s.sale_price is not None:
        return (s.sale_price * s.commission_pct / Decimal("100")).quantize(Decimal("0.01"))
    return Decimal("0")


def _consignor_share(s: ConsignmentSale) -> Decimal:
    price = s.sale_price or Decimal("0")
    comm = _commission_effective(s)
    fee = s.fee_amount or Decimal("0")
    ship = s.shipping_cost or Decimal("0")
    return price - comm - fee - ship


def _to_response(s: ConsignmentSale) -> ConsignmentSaleResponse:
    return ConsignmentSaleResponse(
        id=s.id,
        sale_date=s.sale_date,
        item=s.item,
        consignor=s.consignor,
        sale_price=s.sale_price,
        commission_pct=s.commission_pct,
        commission_amount=s.commission_amount,
        fee_amount=s.fee_amount,
        shipping_cost=s.shipping_cost,
        sold_platform=s.sold_platform,
        sold_by=s.sold_by,
        buyer=s.buyer,
        paid_out=s.paid_out,
        payout_date=s.payout_date,
        note=s.note,
        commission_effective=_commission_effective(s),
        consignor_share=_consignor_share(s),
        created_at=s.created_at.isoformat() if s.created_at else "",
        updated_at=s.updated_at.isoformat() if s.updated_at else "",
    )


@router.get("/", response_model=ConsignmentListResponse)
def list_sales(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    consignor: Optional[str] = Query(None),
    paid_out: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    helper: ConsignmentSaleHelper = Depends(get_consignment_sale_helper),
    _admin: User = Depends(require_admin),
):
    items = helper.gets(year=year, consignor=consignor, paid_out=paid_out, search=search)
    total_sales = Decimal("0")
    total_commission = Decimal("0")
    total_owed = Decimal("0")
    total_paid = Decimal("0")

    bd: dict[str, ConsignorBreakdown] = {}
    for s in items:
        comm = _commission_effective(s)
        share = _consignor_share(s)
        total_sales += s.sale_price or Decimal("0")
        total_commission += comm
        if s.paid_out:
            total_paid += share
        else:
            total_owed += share

        b = bd.setdefault(s.consignor, ConsignorBreakdown(name=s.consignor))
        b.sales_count += 1
        b.sales_total += s.sale_price or Decimal("0")
        b.commission_kept += comm
        if s.paid_out:
            b.paid_already += share
        else:
            b.owed += share

    by_consignor = sorted(bd.values(), key=lambda b: b.sales_total, reverse=True)

    return ConsignmentListResponse(
        items=[_to_response(s) for s in items],
        total=len(items),
        total_sales=total_sales,
        total_commission=total_commission,
        total_owed=total_owed,
        total_paid=total_paid,
        by_consignor=by_consignor,
    )


@router.post("/", response_model=ConsignmentSaleResponse, status_code=status.HTTP_201_CREATED)
def create_sale(
    payload: ConsignmentSaleCreate,
    helper: ConsignmentSaleHelper = Depends(get_consignment_sale_helper),
    _admin: User = Depends(require_admin),
):
    sale = ConsignmentSale(**payload.model_dump())
    sale.item = sale.item.strip()
    sale.consignor = sale.consignor.strip()
    helper.save(sale)
    return _to_response(sale)


@router.patch("/{sale_id}", response_model=ConsignmentSaleResponse)
def update_sale(
    sale_id: int,
    payload: ConsignmentSaleUpdate,
    helper: ConsignmentSaleHelper = Depends(get_consignment_sale_helper),
    _admin: User = Depends(require_admin),
):
    sale = helper.get(sale_id)
    if not sale:
        raise HTTPException(404, f"Vendita {sale_id} non trovata")
    helper.update(payload, sale)
    return _to_response(sale)


@router.post("/{sale_id}/mark-paid", response_model=ConsignmentSaleResponse)
def mark_paid(
    sale_id: int,
    payload: MarkPaidRequest,
    helper: ConsignmentSaleHelper = Depends(get_consignment_sale_helper),
    _admin: User = Depends(require_admin),
):
    """Marca la vendita come saldata al committente."""
    sale = helper.get(sale_id)
    if not sale:
        raise HTTPException(404, f"Vendita {sale_id} non trovata")
    update = ConsignmentSaleUpdate(
        paid_out=True,
        payout_date=payload.payout_date or _date.today(),
    )
    helper.update(update, sale)
    return _to_response(sale)


@router.delete("/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sale(
    sale_id: int,
    helper: ConsignmentSaleHelper = Depends(get_consignment_sale_helper),
    _admin: User = Depends(require_admin),
):
    sale = helper.get(sale_id)
    if not sale:
        raise HTTPException(404, f"Vendita {sale_id} non trovata")
    helper.delete(sale)
    return None
