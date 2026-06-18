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
    MiscSale,
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
