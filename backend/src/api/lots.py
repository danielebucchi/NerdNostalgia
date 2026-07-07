"""
API endpoint Lots (container di inventory_items, admin only).

CRUD lots, distribute_cost, bulk_publish (crea Article DRAFT per piu' item),
e KPI aggregati per ogni lotto.
"""
from collections import Counter
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from helpers.inventory import InventoryHelper, get_inventory_helper
from helpers.lot import LotHelper, get_lot_helper
from models.db import (
    Article,
    ArticleCondition,
    ArticleStatus,
    InventoryItem,
    InventoryItemStatus,
    Lot,
    User,
)
from models.entities.lot import (
    BulkPublishRequest,
    BulkPublishResponse,
    DistributeLotCostRequest,
    DistributeLotCostResponse,
    DuplicateLotRequest,
    LotCreate,
    LotListResponse,
    LotResponse,
    LotUpdate,
)
from utils.session import get_db

router = APIRouter(prefix="/api/lots", tags=["lots"])


def _compute_kpi(lot: Lot) -> dict:
    items = lot.items or []
    qty_total = sum((it.quantity or 0) for it in items)
    qty_sold = sum((it.quantity_sold or 0) for it in items)
    cost_sum = sum(
        ((it.cost or Decimal("0")) * Decimal(it.quantity or 1) for it in items),
        Decimal("0"),
    )
    revenue_sum = Decimal("0")
    profit_sum = Decimal("0")
    immobilizzato = Decimal("0")
    for it in items:
        is_sold = (
            it.status == InventoryItemStatus.SOLD
            or it.sold_date is not None
            or (it.quantity_sold or 0) >= (it.quantity or 0)
        )
        price = it.sale_price or Decimal("0")
        fee = it.fee_amount or Decimal("0")
        ship = it.shipping_cost or Decimal("0")
        cost = it.cost or Decimal("0")
        if is_sold:
            net = price - fee - ship
            revenue_sum += price
            profit_sum += net - cost
        else:
            immobilizzato += cost * Decimal(it.quantity or 1)

    status_breakdown = Counter(it.status for it in items)
    return {
        "items_count": len(items),
        "quantity_total": qty_total,
        "quantity_sold": qty_sold,
        "cost_sum": cost_sum,
        "revenue_sum": revenue_sum,
        "profit_sum": profit_sum,
        "immobilizzato": immobilizzato,
        "status_breakdown": dict(status_breakdown),
    }


def _to_response(lot: Lot) -> LotResponse:
    kpi = _compute_kpi(lot)
    return LotResponse(
        id=lot.id,
        code=lot.code,
        title=lot.title,
        purchase_date=lot.purchase_date,
        purchase_platform=lot.purchase_platform,
        bought_by=lot.bought_by,
        total_cost=lot.total_cost,
        notes=lot.notes,
        status=lot.status,
        items_count=kpi["items_count"],
        quantity_total=kpi["quantity_total"],
        quantity_sold=kpi["quantity_sold"],
        cost_sum=kpi["cost_sum"],
        revenue_sum=kpi["revenue_sum"],
        profit_sum=kpi["profit_sum"],
        immobilizzato=kpi["immobilizzato"],
        status_breakdown=kpi["status_breakdown"],
        created_at=lot.created_at.isoformat() if lot.created_at else None,
        updated_at=lot.updated_at.isoformat() if lot.updated_at else None,
    )


@router.get("/", response_model=LotListResponse)
def list_lots(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    helper: LotHelper = Depends(get_lot_helper),
    _admin: User = Depends(require_admin),
):
    lots = helper.gets(status=status_filter, search=search)
    return LotListResponse(items=[_to_response(lot) for lot in lots], total=len(lots))


@router.get("/{lot_id}", response_model=LotResponse)
def get_lot(
    lot_id: int,
    helper: LotHelper = Depends(get_lot_helper),
    _admin: User = Depends(require_admin),
):
    lot = helper.get(lot_id)
    if not lot:
        raise HTTPException(404, f"Lot {lot_id} non trovato")
    return _to_response(lot)


@router.post("/", response_model=LotResponse, status_code=status.HTTP_201_CREATED)
def create_lot(
    payload: LotCreate,
    helper: LotHelper = Depends(get_lot_helper),
    _admin: User = Depends(require_admin),
):
    lot = Lot(**payload.model_dump())
    helper.save(lot)
    return _to_response(lot)


@router.patch("/{lot_id}", response_model=LotResponse)
def update_lot(
    lot_id: int,
    payload: LotUpdate,
    helper: LotHelper = Depends(get_lot_helper),
    _admin: User = Depends(require_admin),
):
    lot = helper.get(lot_id)
    if not lot:
        raise HTTPException(404, f"Lot {lot_id} non trovato")
    helper.update(payload, lot)
    return _to_response(lot)


@router.delete("/{lot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lot(
    lot_id: int,
    helper: LotHelper = Depends(get_lot_helper),
    _admin: User = Depends(require_admin),
):
    lot = helper.get(lot_id)
    if not lot:
        raise HTTPException(404, f"Lot {lot_id} non trovato")
    if lot.items:
        raise HTTPException(
            400,
            "Lot non vuoto: rimuovi prima tutti gli item, oppure imposta status=ARCHIVED.",
        )
    helper.delete(lot)
    return None


@router.post("/{lot_id}/distribute-cost", response_model=DistributeLotCostResponse)
def distribute_cost(
    lot_id: int,
    payload: DistributeLotCostRequest,
    db: Session = Depends(get_db),
    helper: LotHelper = Depends(get_lot_helper),
    _admin: User = Depends(require_admin),
):
    """Distribuisce total_cost su tutti gli item del Lot, pesato per quantita'.

    unit_cost = total_cost / SUM(quantity). Salva anche total_cost sul Lot.
    """
    lot = helper.get(lot_id)
    if not lot:
        raise HTTPException(404, f"Lot {lot_id} non trovato")
    if not lot.items:
        raise HTTPException(400, "Lot vuoto, niente da distribuire")
    if payload.total_cost < 0:
        raise HTTPException(400, "Costo non puo' essere negativo")

    total_pieces = sum((it.quantity or 1) for it in lot.items)
    if total_pieces <= 0:
        raise HTTPException(400, "Quantita' totali zero")

    unit_cost = (payload.total_cost / total_pieces).quantize(Decimal("0.01"))
    for it in lot.items:
        it.cost = unit_cost
    lot.total_cost = payload.total_cost
    db.commit()

    return DistributeLotCostResponse(
        lot_id=lot.id,
        items_updated=len(lot.items),
        total_pieces=total_pieces,
        unit_cost=unit_cost,
    )


@router.post("/{lot_id}/bulk-publish", response_model=BulkPublishResponse)
def bulk_publish(
    lot_id: int,
    payload: BulkPublishRequest,
    db: Session = Depends(get_db),
    helper: LotHelper = Depends(get_lot_helper),
    inv_helper: InventoryHelper = Depends(get_inventory_helper),
    admin: User = Depends(require_admin),
):
    """Crea Article DRAFT in batch per la lista item_ids del Lot."""
    lot = helper.get(lot_id)
    if not lot:
        raise HTTPException(404, f"Lot {lot_id} non trovato")

    valid_item_ids = {it.id for it in lot.items}
    created = 0
    skipped = 0
    created_ids = []
    for item_id in payload.item_ids:
        if item_id not in valid_item_ids:
            skipped += 1
            continue
        item = inv_helper.get(item_id)
        if not item:
            skipped += 1
            continue
        if item.article_id is not None:
            existing = db.query(Article).filter(Article.id == item.article_id).first()
            if existing:
                skipped += 1
                continue
            item.article_id = None

        article = Article(
            user_id=admin.id,
            title=item.title,
            description=item.description,
            price=item.sale_price or Decimal("0"),
            currency="EUR",
            condition=ArticleCondition.USED,
            status=ArticleStatus.DRAFT,
            quantity=item.quantity,
            category_id=item.category_id,
            images=item.images or [],
            lotto=lot.code,
            purchase_date=lot.purchase_date,
            cost=item.cost,
            purchase_platform=lot.purchase_platform,
            bought_by=lot.bought_by,
            sold_by=item.sold_by,
            fee_amount=item.fee_amount,
            shipping_cost=item.shipping_cost,
            quantity_sold=item.quantity_sold or 0,
            card_collection=item.card_collection,
            card_number=item.card_number,
            card_finish=item.card_finish,
        )
        db.add(article)
        db.flush()
        item.article_id = article.id
        item.status = InventoryItemStatus.LINKED
        created += 1
        created_ids.append(item.id)

    db.commit()
    return BulkPublishResponse(
        created=created, skipped=skipped, item_ids_created=created_ids
    )


@router.post("/{lot_id}/duplicate", response_model=LotResponse, status_code=status.HTTP_201_CREATED)
def duplicate_lot(
    lot_id: int,
    payload: DuplicateLotRequest,
    db: Session = Depends(get_db),
    helper: LotHelper = Depends(get_lot_helper),
    _admin: User = Depends(require_admin),
):
    """Clona un lotto come template. Il nuovo lotto parte OPEN con code nuovo.
    Gli item copiati partono in DRAFT senza foto, senza vendite, con list_price
    e cost invariati (utile per rifornimenti di stesso tipo prodotto)."""
    src = helper.get(lot_id)
    if not src:
        raise HTTPException(404, f"Lot {lot_id} non trovato")

    dup = Lot(
        title=(payload.title_prefix + (src.title or src.code)) if payload.title_prefix else src.title,
        purchase_date=src.purchase_date,
        purchase_platform=src.purchase_platform,
        bought_by=src.bought_by,
        total_cost=src.total_cost,
        notes=src.notes,
        # status e code li setta helper.save()
    )
    helper.save(dup)

    if payload.copy_items:
        for it in src.items:
            clone = InventoryItem(
                lot_id=dup.id,
                title=it.title,
                description=it.description,
                cost=it.cost,
                list_price=it.list_price,
                quantity=it.quantity,
                # nulla di venduto sul clone:
                quantity_sold=0,
                sold_date=None,
                sold_by=None,
                sold_platform=None,
                sale_price=None,
                fee_amount=None,
                shipping_cost=it.shipping_cost,
                status=InventoryItemStatus.DRAFT,
                category_id=it.category_id,
                card_collection=it.card_collection,
                card_number=it.card_number,
                card_finish=it.card_finish,
                notes=it.notes,
                # foto e link article NON copiati: sono specifici del pezzo,
                # non del "tipo" articolo che stiamo replicando.
                images=[],
                article_id=None,
                vinted_item_id=None,
            )
            db.add(clone)
        db.commit()
        db.refresh(dup)

    return _to_response(dup)
