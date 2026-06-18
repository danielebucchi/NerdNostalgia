"""
Entities Pydantic per PersonalCard (carte sciolte, no flipping).
Comprate al kg, vendute singolarmente.
"""
from datetime import date
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


PersonalCardStatusLiteral = Literal[
    "IN_STOCK", "RESERVED", "SOLD", "ARCHIVED"
]


class PersonalCardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    collection: Optional[str] = Field(None, max_length=100)
    card_number: Optional[str] = Field(None, max_length=50)
    finish: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field("IT", max_length=20)
    condition: Optional[str] = Field(None, max_length=20)
    grading: Optional[str] = Field(None, max_length=20)
    owned_by: Optional[str] = Field(None, max_length=20)
    quantity: int = Field(1, ge=0)

    purchase_date: Optional[date] = None
    purchase_cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    purchase_source: Optional[str] = Field(None, max_length=50)
    bulk_source: Optional[str] = Field(None, max_length=100)

    estimated_value: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    estimated_value_updated_at: Optional[date] = None

    status: PersonalCardStatusLiteral = "IN_STOCK"
    sold_date: Optional[date] = None
    sold_by: Optional[str] = Field(None, max_length=20)
    sold_platform: Optional[str] = Field(None, max_length=50)
    sale_price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    fee_amount: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    shipping_cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)

    images: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class PersonalCardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    collection: Optional[str] = Field(None, max_length=100)
    card_number: Optional[str] = Field(None, max_length=50)
    finish: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=20)
    condition: Optional[str] = Field(None, max_length=20)
    grading: Optional[str] = Field(None, max_length=20)
    owned_by: Optional[str] = Field(None, max_length=20)
    quantity: Optional[int] = Field(None, ge=0)
    purchase_date: Optional[date] = None
    purchase_cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    purchase_source: Optional[str] = Field(None, max_length=50)
    bulk_source: Optional[str] = Field(None, max_length=100)
    estimated_value: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    estimated_value_updated_at: Optional[date] = None
    status: Optional[PersonalCardStatusLiteral] = None
    sold_date: Optional[date] = None
    sold_by: Optional[str] = Field(None, max_length=20)
    sold_platform: Optional[str] = Field(None, max_length=50)
    sale_price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    fee_amount: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    shipping_cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    images: Optional[List[str]] = None
    notes: Optional[str] = None


class PersonalCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    collection: Optional[str]
    card_number: Optional[str]
    finish: Optional[str]
    language: Optional[str]
    condition: Optional[str]
    grading: Optional[str]
    owned_by: Optional[str]
    quantity: int

    purchase_date: Optional[date]
    purchase_cost: Optional[Decimal]
    purchase_source: Optional[str]
    bulk_source: Optional[str]

    estimated_value: Optional[Decimal]
    estimated_value_updated_at: Optional[date]

    status: PersonalCardStatusLiteral
    sold_date: Optional[date]
    sold_by: Optional[str]
    sold_platform: Optional[str]
    sale_price: Optional[Decimal]
    fee_amount: Optional[Decimal]
    shipping_cost: Optional[Decimal]

    images: List[str] = Field(default_factory=list)
    notes: Optional[str]

    # Derived
    net_revenue: Optional[Decimal] = None
    profit: Optional[Decimal] = None

    created_at: str
    updated_at: str


class PersonalCardListResponse(BaseModel):
    items: List[PersonalCardResponse]
    total: int
    # KPI stock
    in_stock_count: int = 0
    in_stock_value: Decimal = Decimal("0")
    # KPI vendite
    sold_count: int = 0
    sold_revenue: Decimal = Decimal("0")
    sold_profit: Decimal = Decimal("0")
    total_purchase_cost: Decimal = Decimal("0")


class BulkPurchaseRequest(BaseModel):
    """Distribuisce un costo bulk su un gruppo di carte (stesso bulk_source).

    unit_cost = total_cost / sum(quantity).
    """
    bulk_source: str = Field(..., min_length=1, max_length=100)
    total_cost: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)


class BulkPurchaseResponse(BaseModel):
    bulk_source: str
    cards_updated: int
    total_pieces: int
    unit_cost: Decimal
