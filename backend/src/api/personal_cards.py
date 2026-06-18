"""
API endpoint personal_cards (carte sciolte: bulk-buy, single-sell). Admin only.
"""
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from helpers.personal_card import PersonalCardHelper, get_personal_card_helper
from models.db import PersonalCard, PersonalCardStatus, User
from models.entities.personal_card import (
    BulkPurchaseRequest,
    BulkPurchaseResponse,
    PersonalCardCreate,
    PersonalCardListResponse,
    PersonalCardResponse,
    PersonalCardUpdate,
)
from utils.session import get_db

router = APIRouter(prefix="/api/personal-cards", tags=["personal-cards"])


def _net_revenue(card: PersonalCard) -> Decimal:
    if card.status != PersonalCardStatus.SOLD:
        return Decimal("0")
    return (card.sale_price or Decimal("0")) - (card.fee_amount or Decimal("0")) - (card.shipping_cost or Decimal("0"))


def _profit(card: PersonalCard) -> Decimal:
    if card.status != PersonalCardStatus.SOLD:
        return Decimal("0")
    return _net_revenue(card) - (card.purchase_cost or Decimal("0"))


def _to_response(card: PersonalCard) -> PersonalCardResponse:
    resp = PersonalCardResponse.model_validate(card)
    resp.net_revenue = _net_revenue(card)
    resp.profit = _profit(card)
    return resp


@router.get("/", response_model=PersonalCardListResponse)
def list_cards(
    owned_by: Optional[str] = Query(None),
    collection: Optional[str] = Query(None),
    bulk_source: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    helper: PersonalCardHelper = Depends(get_personal_card_helper),
    _admin: User = Depends(require_admin),
):
    items = helper.gets(
        owned_by=owned_by,
        collection=collection,
        bulk_source=bulk_source,
        status=status_filter,
        search=search,
    )

    in_stock_count = 0
    in_stock_value = Decimal("0")
    sold_count = 0
    sold_revenue = Decimal("0")
    sold_profit = Decimal("0")
    total_cost = Decimal("0")

    for c in items:
        qty = c.quantity or 1
        cost = (c.purchase_cost or Decimal("0")) * Decimal(qty)
        total_cost += cost
        if c.status == PersonalCardStatus.SOLD:
            sold_count += qty
            sold_revenue += c.sale_price or Decimal("0")
            sold_profit += _profit(c)
        elif c.status in (PersonalCardStatus.IN_STOCK, PersonalCardStatus.RESERVED):
            in_stock_count += qty
            in_stock_value += (c.estimated_value or Decimal("0")) * Decimal(qty)

    return PersonalCardListResponse(
        items=[_to_response(c) for c in items],
        total=len(items),
        in_stock_count=in_stock_count,
        in_stock_value=in_stock_value,
        sold_count=sold_count,
        sold_revenue=sold_revenue,
        sold_profit=sold_profit,
        total_purchase_cost=total_cost,
    )


@router.post("/", response_model=PersonalCardResponse, status_code=status.HTTP_201_CREATED)
def create_card(
    payload: PersonalCardCreate,
    helper: PersonalCardHelper = Depends(get_personal_card_helper),
    _admin: User = Depends(require_admin),
):
    """Crea una carta vendita.

    Default: status=SOLD + sold_date=oggi se non specificati. Questa tabella
    e' un log di vendite di carte sciolte (no lotti).
    """
    from datetime import date as _date
    card = PersonalCard(**payload.model_dump())
    card.name = card.name.strip()
    if card.status == PersonalCardStatus.IN_STOCK and not card.sold_date:
        # Default: ogni nuova riga e' una vendita registrata
        card.status = PersonalCardStatus.SOLD
        card.sold_date = _date.today()
    helper.save(card)
    return _to_response(card)


@router.patch("/{card_id}", response_model=PersonalCardResponse)
def update_card(
    card_id: int,
    payload: PersonalCardUpdate,
    helper: PersonalCardHelper = Depends(get_personal_card_helper),
    _admin: User = Depends(require_admin),
):
    card = helper.get(card_id)
    if not card:
        raise HTTPException(404, f"Card {card_id} non trovata")
    helper.update(payload, card)
    return _to_response(card)


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(
    card_id: int,
    helper: PersonalCardHelper = Depends(get_personal_card_helper),
    _admin: User = Depends(require_admin),
):
    card = helper.get(card_id)
    if not card:
        raise HTTPException(404, f"Card {card_id} non trovata")
    helper.delete(card)
    return None


@router.post("/distribute-bulk-cost", response_model=BulkPurchaseResponse)
def distribute_bulk_cost(
    payload: BulkPurchaseRequest,
    db: Session = Depends(get_db),
    helper: PersonalCardHelper = Depends(get_personal_card_helper),
    _admin: User = Depends(require_admin),
):
    """Distribuisce un costo bulk su tutte le carte con stesso bulk_source.

    Usalo dopo aver caricato le carte di un acquisto al kg: assegna a ciascuna
    carta un costo unitario = total_cost / SUM(qty).
    """
    bulk = payload.bulk_source.strip()
    if not bulk:
        raise HTTPException(400, "bulk_source obbligatorio")

    cards = helper.gets(bulk_source=bulk)
    if not cards:
        raise HTTPException(404, f"Nessuna carta con bulk_source '{bulk}'")

    total_pieces = sum((c.quantity or 1) for c in cards)
    if total_pieces <= 0:
        raise HTTPException(400, "Quantita' totali zero")

    unit_cost = (payload.total_cost / total_pieces).quantize(Decimal("0.01"))
    for c in cards:
        c.purchase_cost = unit_cost
    db.commit()

    return BulkPurchaseResponse(
        bulk_source=bulk,
        cards_updated=len(cards),
        total_pieces=total_pieces,
        unit_cost=unit_cost,
    )
