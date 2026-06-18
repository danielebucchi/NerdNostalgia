"""Entities Pydantic per ConsignmentSale."""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ConsignmentSaleCreate(BaseModel):
    sale_date: date
    item: str = Field(..., min_length=1, max_length=255)
    consignor: str = Field(..., min_length=1, max_length=100)
    sale_price: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)
    commission_pct: Optional[Decimal] = Field(None, ge=0, le=100, max_digits=5, decimal_places=2)
    commission_amount: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    fee_amount: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    shipping_cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    sold_platform: Optional[str] = Field(None, max_length=50)
    sold_by: Optional[str] = Field(None, max_length=20)
    buyer: Optional[str] = Field(None, max_length=100)
    paid_out: bool = False
    payout_date: Optional[date] = None
    note: Optional[str] = None


class ConsignmentSaleUpdate(BaseModel):
    sale_date: Optional[date] = None
    item: Optional[str] = Field(None, min_length=1, max_length=255)
    consignor: Optional[str] = Field(None, min_length=1, max_length=100)
    sale_price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    commission_pct: Optional[Decimal] = Field(None, ge=0, le=100, max_digits=5, decimal_places=2)
    commission_amount: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    fee_amount: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    shipping_cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    sold_platform: Optional[str] = Field(None, max_length=50)
    sold_by: Optional[str] = Field(None, max_length=20)
    buyer: Optional[str] = Field(None, max_length=100)
    paid_out: Optional[bool] = None
    payout_date: Optional[date] = None
    note: Optional[str] = None


class ConsignmentSaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sale_date: date
    item: str
    consignor: str
    sale_price: Decimal
    commission_pct: Optional[Decimal]
    commission_amount: Optional[Decimal]
    fee_amount: Optional[Decimal]
    shipping_cost: Optional[Decimal]
    sold_platform: Optional[str]
    sold_by: Optional[str]
    buyer: Optional[str]
    paid_out: bool
    payout_date: Optional[date]
    note: Optional[str]

    # Derived
    commission_effective: Decimal = Decimal("0")  # importo commissione (calcolato o esplicito)
    consignor_share: Decimal = Decimal("0")       # quanto devo al committente

    created_at: str
    updated_at: str


class ConsignorBreakdown(BaseModel):
    name: str
    sales_count: int = 0
    sales_total: Decimal = Decimal("0")
    commission_kept: Decimal = Decimal("0")
    owed: Decimal = Decimal("0")           # da pagare (paid_out=False)
    paid_already: Decimal = Decimal("0")   # gia' pagato


class ConsignmentListResponse(BaseModel):
    items: List[ConsignmentSaleResponse]
    total: int
    total_sales: Decimal = Decimal("0")
    total_commission: Decimal = Decimal("0")
    total_owed: Decimal = Decimal("0")        # da girare al committente
    total_paid: Decimal = Decimal("0")        # gia' girato
    by_consignor: List[ConsignorBreakdown] = Field(default_factory=list)


class MarkPaidRequest(BaseModel):
    payout_date: Optional[date] = None
