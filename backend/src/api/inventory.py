"""
API endpoint inventory_items (singolo item interno al lotto, admin only).

CRUD piu' publish_to_site (crea Article DRAFT) e unpublish (scollega).
La gestione del Lot e dei suoi metadati comuni sta in api/lots.py.
"""
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
    Category,
    InventoryItem,
    InventoryItemStatus,
    User,
)
from models.entities.category import CategoryResponse
from models.entities.inventory import (
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryItemUpdate,
    InventoryListResponse,
    PublishToSiteRequest,
    StatusUpdateRequest,
)
from utils.session import get_db

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


def _category_to_response(cat: Optional[Category]) -> Optional[CategoryResponse]:
    if cat is None:
        return None
    return CategoryResponse(
        id=cat.id,
        name=cat.name,
        slug=cat.slug,
        parent_id=cat.parent_id,
        display_order=cat.display_order,
    )


def _calc_metrics(item: InventoryItem) -> dict:
    price = item.sale_price or Decimal("0")
    fee = item.fee_amount or Decimal("0")
    ship = item.shipping_cost or Decimal("0")
    cost = item.cost or Decimal("0")

    sold = item.status == InventoryItemStatus.SOLD or (
        item.sold_date is not None or (item.quantity_sold or 0) >= item.quantity
    )
    net_revenue = (price - fee - ship) if sold else Decimal("0")
    profit = (net_revenue - cost) if sold else Decimal("0")
    immobilizzato = cost if (not sold and cost > 0) else Decimal("0")
    ancora_disponibile = (
        item.status not in (InventoryItemStatus.SOLD, InventoryItemStatus.ARCHIVED)
        and (item.quantity - (item.quantity_sold or 0)) > 0
    )
    return {
        "net_revenue": net_revenue,
        "profit": profit,
        "immobilizzato": immobilizzato,
        "ancora_disponibile": ancora_disponibile,
    }


def _to_response(item: InventoryItem) -> InventoryItemResponse:
    parent_cat = item.category.parent if item.category and item.category.parent else None
    m = _calc_metrics(item)
    lot_code = item.lot.code if item.lot else None
    lot_title = item.lot.title if item.lot else None
    return InventoryItemResponse(
        id=item.id,
        lot_id=item.lot_id,
        lot_code=lot_code,
        lot_title=lot_title,
        title=item.title,
        description=item.description,
        cost=item.cost,
        sold_date=item.sold_date,
        sold_by=item.sold_by,
        sold_platform=item.sold_platform,
        sale_price=item.sale_price,
        fee_amount=item.fee_amount,
        shipping_cost=item.shipping_cost,
        status=item.status,
        quantity=item.quantity,
        quantity_sold=item.quantity_sold or 0,
        category_id=item.category_id,
        category=_category_to_response(item.category),
        parent_category=_category_to_response(parent_cat),
        card_collection=item.card_collection,
        card_number=item.card_number,
        card_finish=item.card_finish,
        article_id=item.article_id,
        vinted_item_id=item.vinted_item_id,
        images=item.images or [],
        notes=item.notes,
        net_revenue=m["net_revenue"],
        profit=m["profit"],
        immobilizzato=m["immobilizzato"],
        ancora_disponibile=m["ancora_disponibile"],
        created_at=item.created_at.isoformat() if item.created_at else None,
        updated_at=item.updated_at.isoformat() if item.updated_at else None,
    )


@router.get("/", response_model=InventoryListResponse)
def list_items(
    lot_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None, ge=2000, le=2100),
    category_id: Optional[int] = Query(None),
    sold_only: Optional[bool] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=500),
    helper: InventoryHelper = Depends(get_inventory_helper),
    _admin: User = Depends(require_admin),
):
    items = helper.gets(
        lot_id=lot_id,
        year=year,
        category_id=category_id,
        sold_only=sold_only,
        status=status_filter,
        search=search,
        limit=limit,
    )
    responses = [_to_response(i) for i in items]
    total_cost = sum((Decimal(r.cost or 0) for r in responses), Decimal("0"))
    total_revenue = sum(
        (Decimal(r.sale_price or 0) for r in responses if r.sold_date),
        Decimal("0"),
    )
    total_profit = sum(
        (Decimal(r.profit or 0) for r in responses), Decimal("0"),
    )
    total_immobilizzato = sum(
        (Decimal(r.immobilizzato or 0) for r in responses), Decimal("0"),
    )
    return InventoryListResponse(
        items=responses,
        total=len(responses),
        total_cost=total_cost,
        total_revenue=total_revenue,
        total_profit=total_profit,
        total_immobilizzato=total_immobilizzato,
    )


@router.post("/", response_model=InventoryItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: InventoryItemCreate,
    helper: InventoryHelper = Depends(get_inventory_helper),
    lot_helper: LotHelper = Depends(get_lot_helper),
    _admin: User = Depends(require_admin),
):
    if not lot_helper.get(payload.lot_id):
        raise HTTPException(404, f"Lot {payload.lot_id} non trovato")
    item = InventoryItem(**payload.model_dump())
    item.title = item.title.strip()
    helper.save(item)
    return _to_response(item)


@router.patch("/{item_id}", response_model=InventoryItemResponse)
def update_item(
    item_id: int,
    payload: InventoryItemUpdate,
    helper: InventoryHelper = Depends(get_inventory_helper),
    lot_helper: LotHelper = Depends(get_lot_helper),
    _admin: User = Depends(require_admin),
):
    item = helper.get(item_id)
    if not item:
        raise HTTPException(404, f"Lot item {item_id} non trovato")
    if payload.lot_id is not None and payload.lot_id != item.lot_id:
        if not lot_helper.get(payload.lot_id):
            raise HTTPException(404, f"Lot {payload.lot_id} non trovato")
    helper.update(payload, item)
    return _to_response(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    helper: InventoryHelper = Depends(get_inventory_helper),
    _admin: User = Depends(require_admin),
):
    item = helper.get(item_id)
    if not item:
        raise HTTPException(404, f"Lot item {item_id} non trovato")
    helper.delete(item)
    return None


@router.patch("/{item_id}/status", response_model=InventoryItemResponse)
def update_status(
    item_id: int,
    payload: StatusUpdateRequest,
    db: Session = Depends(get_db),
    helper: InventoryHelper = Depends(get_inventory_helper),
    _admin: User = Depends(require_admin),
):
    """Cambio stato manuale (es. RESERVED, ARCHIVED)."""
    item = helper.get(item_id)
    if not item:
        raise HTTPException(404, f"Lot item {item_id} non trovato")
    item.status = payload.status
    db.commit()
    db.refresh(item)
    return _to_response(item)


@router.post("/{item_id}/publish", response_model=InventoryItemResponse)
def publish_to_site(
    item_id: int,
    payload: PublishToSiteRequest,
    db: Session = Depends(get_db),
    helper: InventoryHelper = Depends(get_inventory_helper),
    admin: User = Depends(require_admin),
):
    """Crea un Article DRAFT a partire dal lot_item e lo linka via article_id.

    Idempotente: se esiste gia' un article_id valido, restituisce l'item.
    """
    item = helper.get(item_id)
    if not item:
        raise HTTPException(404, f"Lot item {item_id} non trovato")

    if item.article_id is not None:
        existing = db.query(Article).filter(Article.id == item.article_id).first()
        if existing:
            return _to_response(item)
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
        lotto=item.lot.code if item.lot else None,
        purchase_date=item.lot.purchase_date if item.lot else None,
        cost=item.cost,
        purchase_platform=item.lot.purchase_platform if item.lot else None,
        bought_by=item.lot.bought_by if item.lot else None,
        sold_by=item.sold_by,
        fee_amount=item.fee_amount,
        shipping_cost=item.shipping_cost,
        quantity_sold=item.quantity_sold or 0,
        card_collection=item.card_collection,
        card_number=item.card_number,
        card_finish=item.card_finish,
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    item.article_id = article.id
    item.status = InventoryItemStatus.LINKED
    db.commit()
    db.refresh(item)

    return _to_response(item)


@router.post("/{item_id}/unpublish", response_model=InventoryItemResponse)
def unpublish_from_site(
    item_id: int,
    db: Session = Depends(get_db),
    helper: InventoryHelper = Depends(get_inventory_helper),
    _admin: User = Depends(require_admin),
):
    """Stacca l'Article dal lot_item (NON cancella l'Article). Torna in DRAFT."""
    item = helper.get(item_id)
    if not item:
        raise HTTPException(404, f"Lot item {item_id} non trovato")
    item.article_id = None
    if item.status in (InventoryItemStatus.LINKED, InventoryItemStatus.LISTED):
        item.status = InventoryItemStatus.DRAFT
    db.commit()
    db.refresh(item)
    return _to_response(item)
