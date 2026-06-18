"""
API endpoint dashboard admin: totali stile foglio "Esterni" / "TOTALE".
Aggregati ricalcolati a richiesta sul DB.
"""
from datetime import date
from decimal import Decimal
from typing import Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from helpers.auth import require_admin
from models.db import (
    Article,
    ArticleStatus,
    CardPurchase,
    Category,
    ConsignmentSale,
    Expense,
    InventoryItem,
    InventoryItemStatus,
    Lot,
    MiscSale,
    PersonalCard,
    User,
)
from utils.session import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class CategoryTotals(BaseModel):
    revenue: Decimal = Decimal("0")
    cost: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")
    shipping: Decimal = Decimal("0")
    net_revenue: Decimal = Decimal("0")
    profit: Decimal = Decimal("0")
    immobilizzato: Decimal = Decimal("0")
    items_sold: int = 0
    items_available: int = 0


class DashboardTotals(BaseModel):
    year: int
    # Stile "Esterni": per gruppo
    revenue_by_group: Dict[str, Decimal] = Field(default_factory=dict)
    cost_by_group: Dict[str, Decimal] = Field(default_factory=dict)
    profit_by_group: Dict[str, Decimal] = Field(default_factory=dict)
    # Totali generali
    total_revenue: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    total_profit: Decimal = Decimal("0")
    total_immobilizzato: Decimal = Decimal("0")
    # Dettaglio per categoria top-level (carte, videogiochi, nerdate, ecc)
    by_category: Dict[str, CategoryTotals] = Field(default_factory=dict)
    # Contatori operativi
    articles_sold: int = 0
    articles_available: int = 0
    misc_sales_count: int = 0
    card_purchases_count: int = 0


def _safe(v: Optional[Decimal]) -> Decimal:
    return v if v is not None else Decimal("0")


# ============================================================
# /totali — Aggregati da inventory_items (source of truth)
# ============================================================

class CategoryBreakdown(BaseModel):
    slug: str
    name: str
    revenue: Decimal = Decimal("0")
    cost: Decimal = Decimal("0")
    profit: Decimal = Decimal("0")
    immobilizzato: Decimal = Decimal("0")
    items_sold: int = 0
    items_available: int = 0


class PlatformBreakdown(BaseModel):
    label: str
    revenue: Decimal = Decimal("0")
    cost: Decimal = Decimal("0")
    items: int = 0


class PersonBreakdown(BaseModel):
    label: str
    revenue: Decimal = Decimal("0")
    cost: Decimal = Decimal("0")
    items: int = 0


class MonthPoint(BaseModel):
    month: int          # 1..12
    label: str          # "Gen", "Feb", ...
    revenue: Decimal = Decimal("0")
    cost: Decimal = Decimal("0")
    profit: Decimal = Decimal("0")
    items_sold: int = 0


class CollectionRecap(BaseModel):
    """Recap carte sciolte (PersonalCard) — bulk-buy / single-sell.

    Mostra sia lo stock (in attesa di vendita, con valore stimato) sia
    le vendite chiuse nell'anno (revenue + profitto reale).
    """
    # Stock attuale (snapshot)
    in_stock_cards: int = 0
    in_stock_value: Decimal = Decimal("0")
    in_stock_cost: Decimal = Decimal("0")
    # Vendite anno corrente
    sold_count: int = 0
    sold_revenue: Decimal = Decimal("0")
    sold_profit: Decimal = Decimal("0")
    voices_count: int = 0
    by_owner: list[PersonBreakdown] = Field(default_factory=list)


class ExpensesRecap(BaseModel):
    """Recap unificato delle spese di un anno."""
    card_purchases: Decimal = Decimal("0")     # foglio "Spese carte"
    card_purchases_count: int = 0
    other_expenses: Decimal = Decimal("0")     # foglio "Spese" generiche
    other_expenses_count: int = 0
    card_related_other: Decimal = Decimal("0") # spese non-bulk ma flag related_to_cards=True
    creation_related: Decimal = Decimal("0")   # spese flag related_to_creations=True
    total: Decimal = Decimal("0")
    cards_total: Decimal = Decimal("0")        # card_purchases + card_related_other
    creations_total: Decimal = Decimal("0")    # creation_related (per profitto netto creazioni)
    by_category: dict[str, Decimal] = Field(default_factory=dict)


class ConsignmentRecap(BaseModel):
    """Recap vendite in contovendita di un anno."""
    count: int = 0
    sales_total: Decimal = Decimal("0")
    commission_kept: Decimal = Decimal("0")
    owed: Decimal = Decimal("0")
    paid_already: Decimal = Decimal("0")
    by_consignor: list[PersonBreakdown] = Field(default_factory=list)


class CreationsRecap(BaseModel):
    """Recap creazioni handmade (MiscSale.kind='creation')."""
    count: int = 0
    revenue: Decimal = Decimal("0")
    material_cost: Decimal = Decimal("0")     # somma material_cost per-vendita
    gross_profit: Decimal = Decimal("0")      # revenue - material_cost
    by_seller: list[PersonBreakdown] = Field(default_factory=list)
    by_platform: list[PlatformBreakdown] = Field(default_factory=list)


class ExternalSalesRecap(BaseModel):
    """Recap delle vendite esterne (MiscSale) di un anno."""
    total: Decimal = Decimal("0")
    paid: Decimal = Decimal("0")
    unpaid: Decimal = Decimal("0")
    count: int = 0
    by_seller: list[PersonBreakdown] = Field(default_factory=list)
    by_platform: list[PlatformBreakdown] = Field(default_factory=list)
    monthly: list[MonthPoint] = Field(default_factory=list)


class InventoryTotali(BaseModel):
    year: int
    # KPI
    total_revenue: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    total_profit: Decimal = Decimal("0")
    total_immobilizzato: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")
    total_shipping: Decimal = Decimal("0")
    items_sold: int = 0
    items_available: int = 0
    lots_count: int = 0
    # Side ledger (carte all'ingrosso + vendite varie)
    misc_revenue: Decimal = Decimal("0")
    card_purchases: Decimal = Decimal("0")
    external_sales: ExternalSalesRecap = Field(default_factory=ExternalSalesRecap)
    collection: CollectionRecap = Field(default_factory=CollectionRecap)
    expenses: ExpensesRecap = Field(default_factory=ExpensesRecap)
    creations: CreationsRecap = Field(default_factory=CreationsRecap)
    consignment: ConsignmentRecap = Field(default_factory=ConsignmentRecap)
    # Breakdown
    by_category: list[CategoryBreakdown] = Field(default_factory=list)
    by_sold_platform: list[PlatformBreakdown] = Field(default_factory=list)
    by_purchase_platform: list[PlatformBreakdown] = Field(default_factory=list)
    by_bought_by: list[PersonBreakdown] = Field(default_factory=list)
    by_sold_by: list[PersonBreakdown] = Field(default_factory=list)
    monthly: list[MonthPoint] = Field(default_factory=list)


_MONTH_LABELS = ["", "Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                 "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]


def _is_sold(item: InventoryItem) -> bool:
    return (
        item.status == InventoryItemStatus.SOLD
        or item.sold_date is not None
        or (item.quantity_sold or 0) >= (item.quantity or 0)
    )


@router.get("/totali", response_model=InventoryTotali)
def get_totali(
    year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Aggregati Totali stile foglio, basati su inventory_items (source of truth).

    Logica:
      * Vendite contano nell'anno del sold_date.
      * Immobilizzato = snapshot di tutti gli item non venduti con cost>0
        (lot.purchase_date.year == year). Se nessuna data lotto, contano sempre.
      * Costi (per categoria) = cost*qty di item venduti nell'anno.
    """
    items = (
        db.query(InventoryItem)
        .join(Lot, InventoryItem.lot_id == Lot.id)
        .outerjoin(Category, InventoryItem.category_id == Category.id)
        .all()
    )

    cat_buckets: Dict[str, CategoryBreakdown] = {}
    sold_pf: Dict[str, PlatformBreakdown] = {}
    purchase_pf: Dict[str, PlatformBreakdown] = {}
    bought_by: Dict[str, PersonBreakdown] = {}
    sold_by: Dict[str, PersonBreakdown] = {}
    monthly: Dict[int, MonthPoint] = {
        m: MonthPoint(month=m, label=_MONTH_LABELS[m]) for m in range(1, 13)
    }

    total_revenue = Decimal("0")
    total_cost = Decimal("0")
    total_profit = Decimal("0")
    total_immobilizzato = Decimal("0")
    total_fees = Decimal("0")
    total_shipping = Decimal("0")
    items_sold = 0
    items_available = 0
    seen_lots: set[int] = set()

    for it in items:
        if it.lot_id:
            seen_lots.add(it.lot_id)

        # Categoria top-level
        if it.category:
            top = it.category.parent or it.category
            top_slug = top.slug
            top_name = top.name
        else:
            top_slug = "altro"
            top_name = "Altro"

        bucket = cat_buckets.setdefault(
            top_slug, CategoryBreakdown(slug=top_slug, name=top_name)
        )

        qty = it.quantity or 1
        cost_unit = _safe(it.cost)
        cost_total = cost_unit * Decimal(qty)
        price = _safe(it.sale_price)
        fee = _safe(it.fee_amount)
        ship = _safe(it.shipping_cost)

        sold = _is_sold(it)
        sold_year = it.sold_date.year if it.sold_date else None
        lot_purchase_year = (
            it.lot.purchase_date.year if it.lot and it.lot.purchase_date else None
        )

        # Vendita contabilizzata nell'anno del sold_date
        if sold and sold_year == year:
            net = price - fee - ship
            profit = net - cost_unit  # profitto per unita' venduta (price gia' totale)
            bucket.revenue += price
            bucket.cost += cost_unit
            bucket.profit += profit
            bucket.items_sold += 1

            total_revenue += price
            total_cost += cost_unit
            total_profit += profit
            total_fees += fee
            total_shipping += ship
            items_sold += 1

            # Per piattaforma vendita
            pf = (it.sold_platform or "—").strip() or "—"
            sb = sold_pf.setdefault(pf, PlatformBreakdown(label=pf))
            sb.revenue += price
            sb.cost += cost_unit
            sb.items += 1

            # Per chi vende
            sby = (it.sold_by or "—").strip() or "—"
            pb_sold = sold_by.setdefault(sby, PersonBreakdown(label=sby))
            pb_sold.revenue += price
            pb_sold.cost += cost_unit
            pb_sold.items += 1

            # Mensile
            if it.sold_date:
                mp = monthly[it.sold_date.month]
                mp.revenue += price
                mp.cost += cost_unit
                mp.profit += profit
                mp.items_sold += 1

        # Immobilizzato (snapshot: anno corrente o se nessuna data)
        if not sold and cost_total > 0 and (lot_purchase_year == year or lot_purchase_year is None):
            bucket.immobilizzato += cost_total
            total_immobilizzato += cost_total
            bucket.items_available += 1
            items_available += 1
        elif not sold and (lot_purchase_year == year or lot_purchase_year is None):
            bucket.items_available += 1
            items_available += 1

        # Per piattaforma acquisto + chi compra (sull'anno del Lot)
        if it.lot and lot_purchase_year == year:
            ppf = (it.lot.purchase_platform or "—").strip() or "—"
            ppb = purchase_pf.setdefault(ppf, PlatformBreakdown(label=ppf))
            ppb.cost += cost_total
            ppb.items += 1

            bby = (it.lot.bought_by or "—").strip() or "—"
            pb_b = bought_by.setdefault(bby, PersonBreakdown(label=bby))
            pb_b.cost += cost_total
            pb_b.items += 1

    # Side ledger
    misc_revenue = (
        db.query(func.coalesce(func.sum(MiscSale.amount), 0))
        .filter(extract("year", MiscSale.sale_date) == year)
        .scalar()
    ) or Decimal("0")
    card_purchases = (
        db.query(func.coalesce(func.sum(CardPurchase.amount), 0))
        .filter(extract("year", CardPurchase.purchase_date) == year)
        .scalar()
    ) or Decimal("0")
    card_purchases_count = (
        db.query(func.count(CardPurchase.id))
        .filter(extract("year", CardPurchase.purchase_date) == year)
        .scalar()
    ) or 0

    # Expenses generiche
    expense_rows = (
        db.query(Expense)
        .filter(extract("year", Expense.spend_date) == year)
        .all()
    )
    other_total = Decimal("0")
    card_related_other = Decimal("0")
    creation_related = Decimal("0")
    by_cat: Dict[str, Decimal] = {}
    for e in expense_rows:
        amt = _safe(e.amount)
        other_total += amt
        if e.related_to_cards:
            card_related_other += amt
        if e.related_to_creations:
            creation_related += amt
        cat_key = e.category or "—"
        by_cat[cat_key] = by_cat.get(cat_key, Decimal("0")) + amt

    expenses_recap = ExpensesRecap(
        card_purchases=Decimal(card_purchases),
        card_purchases_count=card_purchases_count,
        other_expenses=other_total,
        other_expenses_count=len(expense_rows),
        card_related_other=card_related_other,
        creation_related=creation_related,
        total=Decimal(card_purchases) + other_total,
        cards_total=Decimal(card_purchases) + card_related_other,
        creations_total=creation_related,
        by_category=by_cat,
    )

    # MiscSale dell'anno: split per kind (external vs creation)
    misc_rows = (
        db.query(MiscSale)
        .filter(extract("year", MiscSale.sale_date) == year)
        .all()
    )
    # External sales (kind='external')
    ext_total = Decimal("0")
    ext_paid = Decimal("0")
    ext_unpaid = Decimal("0")
    ext_count = 0
    ext_by_seller: Dict[str, PersonBreakdown] = {}
    ext_by_platform: Dict[str, PlatformBreakdown] = {}
    ext_monthly: Dict[int, MonthPoint] = {
        m: MonthPoint(month=m, label=_MONTH_LABELS[m]) for m in range(1, 13)
    }
    # Creations (kind='creation')
    cre_revenue = Decimal("0")
    cre_material = Decimal("0")
    cre_count = 0
    cre_by_seller: Dict[str, PersonBreakdown] = {}
    cre_by_platform: Dict[str, PlatformBreakdown] = {}

    for ms in misc_rows:
        amt = _safe(ms.amount)
        sky = (ms.seller or "—").strip() or "—"
        pky = (ms.platform or "—").strip() or "—"

        if (ms.kind or "external") == "creation":
            cre_revenue += amt
            cre_material += _safe(ms.material_cost)
            cre_count += 1
            b = cre_by_seller.setdefault(sky, PersonBreakdown(label=sky))
            b.revenue += amt
            b.cost += _safe(ms.material_cost)
            b.items += 1
            pp = cre_by_platform.setdefault(pky, PlatformBreakdown(label=pky))
            pp.revenue += amt
            pp.items += 1
        else:
            ext_total += amt
            ext_count += 1
            if ms.paid_by_buyer:
                ext_paid += amt
            else:
                ext_unpaid += amt
            b = ext_by_seller.setdefault(sky, PersonBreakdown(label=sky))
            b.revenue += amt
            b.items += 1
            pp = ext_by_platform.setdefault(pky, PlatformBreakdown(label=pky))
            pp.revenue += amt
            pp.items += 1
            if ms.sale_date:
                mp = ext_monthly[ms.sale_date.month]
                mp.revenue += amt
                mp.items_sold += 1

    creations_recap = CreationsRecap(
        count=cre_count,
        revenue=cre_revenue,
        material_cost=cre_material,
        gross_profit=cre_revenue - cre_material,
        by_seller=sorted(cre_by_seller.values(), key=lambda b: b.revenue, reverse=True),
        by_platform=sorted(cre_by_platform.values(), key=lambda b: b.revenue, reverse=True),
    )

    # Contovendita (ConsignmentSale) — anno
    consign_rows = (
        db.query(ConsignmentSale)
        .filter(extract("year", ConsignmentSale.sale_date) == year)
        .all()
    )
    cons_count = 0
    cons_sales = Decimal("0")
    cons_commission = Decimal("0")
    cons_owed = Decimal("0")
    cons_paid = Decimal("0")
    cons_by: Dict[str, PersonBreakdown] = {}
    for cs in consign_rows:
        price = _safe(cs.sale_price)
        if cs.commission_amount is not None:
            comm = cs.commission_amount
        elif cs.commission_pct is not None:
            comm = (price * cs.commission_pct / Decimal("100")).quantize(Decimal("0.01"))
        else:
            comm = Decimal("0")
        share = price - comm - _safe(cs.fee_amount) - _safe(cs.shipping_cost)
        cons_count += 1
        cons_sales += price
        cons_commission += comm
        if cs.paid_out:
            cons_paid += share
        else:
            cons_owed += share
        b = cons_by.setdefault(cs.consignor, PersonBreakdown(label=cs.consignor))
        b.revenue += price
        b.cost += share if not cs.paid_out else Decimal("0")
        b.items += 1

    consignment_recap = ConsignmentRecap(
        count=cons_count,
        sales_total=cons_sales,
        commission_kept=cons_commission,
        owed=cons_owed,
        paid_already=cons_paid,
        by_consignor=sorted(cons_by.values(), key=lambda b: b.revenue, reverse=True),
    )

    # Carte (no flipping) — stock attuale + vendite anno
    personal_rows = db.query(PersonalCard).all()
    in_stock_cards = 0
    in_stock_value = Decimal("0")
    in_stock_cost = Decimal("0")
    sold_count_pc = 0
    sold_revenue_pc = Decimal("0")
    sold_profit_pc = Decimal("0")
    coll_by_owner: Dict[str, PersonBreakdown] = {}

    for pc in personal_rows:
        qty = pc.quantity or 1
        cost_unit = _safe(pc.purchase_cost)
        cost_total = cost_unit * Decimal(qty)
        owner = (pc.owned_by or "—").strip() or "—"
        b = coll_by_owner.setdefault(owner, PersonBreakdown(label=owner))

        if pc.status == "SOLD":
            sold_year_pc = pc.sold_date.year if pc.sold_date else None
            if sold_year_pc == year:
                price = _safe(pc.sale_price)
                net = price - _safe(pc.fee_amount) - _safe(pc.shipping_cost)
                profit = net - cost_unit
                sold_count_pc += qty
                sold_revenue_pc += price
                sold_profit_pc += profit
                b.revenue += price
                b.cost += cost_unit
                b.items += qty
        elif pc.status in ("IN_STOCK", "RESERVED"):
            value = _safe(pc.estimated_value) * Decimal(qty)
            in_stock_cards += qty
            in_stock_value += value
            in_stock_cost += cost_total
            b.cost += cost_total
            b.items += qty

    collection_recap = CollectionRecap(
        in_stock_cards=in_stock_cards,
        in_stock_value=in_stock_value,
        in_stock_cost=in_stock_cost,
        sold_count=sold_count_pc,
        sold_revenue=sold_revenue_pc,
        sold_profit=sold_profit_pc,
        voices_count=len(personal_rows),
        by_owner=sorted(coll_by_owner.values(), key=lambda b: b.revenue, reverse=True),
    )

    external_sales = ExternalSalesRecap(
        total=ext_total,
        paid=ext_paid,
        unpaid=ext_unpaid,
        count=ext_count,
        by_seller=sorted(ext_by_seller.values(), key=lambda b: b.revenue, reverse=True),
        by_platform=sorted(ext_by_platform.values(), key=lambda b: b.revenue, reverse=True),
        monthly=[ext_monthly[m] for m in range(1, 13)],
    )

    # Conta solo lots con almeno un item visto + purchase nell'anno
    lots_count = (
        db.query(func.count(Lot.id))
        .filter(extract("year", Lot.purchase_date) == year)
        .scalar()
    ) or 0

    return InventoryTotali(
        year=year,
        total_revenue=total_revenue,
        total_cost=total_cost,
        total_profit=total_profit,
        total_immobilizzato=total_immobilizzato,
        total_fees=total_fees,
        total_shipping=total_shipping,
        items_sold=items_sold,
        items_available=items_available,
        lots_count=lots_count,
        misc_revenue=Decimal(misc_revenue),
        card_purchases=Decimal(card_purchases),
        external_sales=external_sales,
        collection=collection_recap,
        expenses=expenses_recap,
        creations=creations_recap,
        consignment=consignment_recap,
        by_category=sorted(cat_buckets.values(), key=lambda b: b.revenue, reverse=True),
        by_sold_platform=sorted(sold_pf.values(), key=lambda b: b.revenue, reverse=True),
        by_purchase_platform=sorted(purchase_pf.values(), key=lambda b: b.cost, reverse=True),
        by_bought_by=sorted(bought_by.values(), key=lambda b: b.cost, reverse=True),
        by_sold_by=sorted(sold_by.values(), key=lambda b: b.revenue, reverse=True),
        monthly=[monthly[m] for m in range(1, 13)],
    )


@router.get("/totals", response_model=DashboardTotals)
def get_totals(
    year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Aggregati anno: clona la struttura del foglio Esterni / TOTALE.

    Definizioni (allineate al foglio):
      * SOLD = articolo venduto (Listato=FALSE & Ancora disponibile=NO)
      * net_revenue = price - fee - shipping (solo se SOLD)
      * profit      = net_revenue - cost     (solo se SOLD)
      * immobilizzato = cost (solo se NOT SOLD e cost > 0)
    """
    # Articoli pertinenti all'anno: purchase_date oppure sold_at oppure created_at
    articles = (
        db.query(Article)
        .outerjoin(Category, Article.category_id == Category.id)
        .all()
    )

    by_category: Dict[str, CategoryTotals] = {}
    total_revenue = Decimal("0")
    total_cost = Decimal("0")
    total_profit = Decimal("0")
    total_immobilizzato = Decimal("0")
    articles_sold = 0
    articles_available = 0

    for a in articles:
        # Determina la "top-level slug" (carte/videogiochi/nerdate/...).
        top_slug = "altro"
        top_name = "Altro"
        if a.category:
            top = a.category.parent or a.category
            top_slug = top.slug
            top_name = top.name

        bucket = by_category.setdefault(top_slug, CategoryTotals())
        cost = _safe(a.cost)
        fee = _safe(a.fee_amount)
        ship = _safe(a.shipping_cost)
        price = _safe(a.price)

        sold = a.status == ArticleStatus.SOLD
        sold_year = a.sold_at.year if a.sold_at else None
        purchase_year = a.purchase_date.year if a.purchase_date else None

        # Conteggi su anno corrente: una vendita contribuisce solo nell'anno della vendita
        if sold and sold_year == year:
            bucket.revenue += price
            bucket.cost += cost
            bucket.fees += fee
            bucket.shipping += ship
            net = price - fee - ship
            bucket.net_revenue += net
            bucket.profit += net - cost
            bucket.items_sold += 1
            total_revenue += price
            total_cost += cost
            total_profit += net - cost
            articles_sold += 1

        # Immobilizzato corrente: tutti i non venduti con cost > 0 contano (snapshot)
        if not sold and cost > 0:
            bucket.immobilizzato += cost
            total_immobilizzato += cost
            bucket.items_available += 1
            articles_available += 1
        elif not sold:
            bucket.items_available += 1
            articles_available += 1

    # Spese carte all'ingrosso anno
    card_spese = (
        db.query(func.coalesce(func.sum(CardPurchase.amount), 0))
        .filter(extract("year", CardPurchase.purchase_date) == year)
        .scalar()
    ) or Decimal("0")
    card_purchases_count = (
        db.query(func.count(CardPurchase.id))
        .filter(extract("year", CardPurchase.purchase_date) == year)
        .scalar()
    ) or 0

    # Vendite varie anno (entrano nel ricavo)
    misc_revenue = (
        db.query(func.coalesce(func.sum(MiscSale.amount), 0))
        .filter(extract("year", MiscSale.sale_date) == year)
        .scalar()
    ) or Decimal("0")
    misc_count = (
        db.query(func.count(MiscSale.id))
        .filter(extract("year", MiscSale.sale_date) == year)
        .scalar()
    ) or 0

    revenue_by_group = {slug: b.revenue for slug, b in by_category.items()}
    cost_by_group = {slug: b.cost for slug, b in by_category.items()}
    profit_by_group = {slug: b.profit for slug, b in by_category.items()}
    revenue_by_group["vendite_varie"] = Decimal(misc_revenue)
    cost_by_group["spese_carte"] = Decimal(card_spese)
    profit_by_group["vendite_varie"] = Decimal(misc_revenue)
    profit_by_group["spese_carte"] = -Decimal(card_spese)

    total_revenue += Decimal(misc_revenue)
    total_cost += Decimal(card_spese)
    total_profit += Decimal(misc_revenue) - Decimal(card_spese)

    return DashboardTotals(
        year=year,
        revenue_by_group=revenue_by_group,
        cost_by_group=cost_by_group,
        profit_by_group=profit_by_group,
        total_revenue=total_revenue,
        total_cost=total_cost,
        total_profit=total_profit,
        total_immobilizzato=total_immobilizzato,
        by_category=by_category,
        articles_sold=articles_sold,
        articles_available=articles_available,
        misc_sales_count=misc_count,
        card_purchases_count=card_purchases_count,
    )
