"""
Entities Pydantic per gli inventory_items.

Ogni item appartiene a un Lot (lot_id obbligatorio). I metadati di acquisto
comuni (purchase_date, purchase_platform, bought_by) vivono sul Lot e
NON sono piu' campi dell'item.
"""
from datetime import date
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from models.entities.category import CategoryResponse


InventoryItemStatusLiteral = Literal[
    "DRAFT", "LINKED", "LISTED", "RESERVED", "SOLD", "ARCHIVED"
]


class InventoryItemBase(BaseModel):
    lot_id: int
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)

    sold_date: Optional[date] = None
    sold_by: Optional[str] = Field(None, max_length=20)
    sold_platform: Optional[str] = Field(None, max_length=50)
    sale_price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    fee_amount: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    shipping_cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)

    status: InventoryItemStatusLiteral = "DRAFT"
    quantity: int = Field(1, ge=0)
    quantity_sold: int = Field(0, ge=0)

    category_id: Optional[int] = None

    card_collection: Optional[str] = Field(None, max_length=100)
    card_number: Optional[str] = Field(None, max_length=50)
    card_finish: Optional[str] = Field(None, max_length=50)

    article_id: Optional[int] = None
    vinted_item_id: Optional[int] = None

    images: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemUpdate(BaseModel):
    lot_id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    sold_date: Optional[date] = None
    sold_by: Optional[str] = Field(None, max_length=20)
    sold_platform: Optional[str] = Field(None, max_length=50)
    sale_price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    fee_amount: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    shipping_cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    status: Optional[InventoryItemStatusLiteral] = None
    quantity: Optional[int] = Field(None, ge=0)
    quantity_sold: Optional[int] = Field(None, ge=0)
    category_id: Optional[int] = None
    card_collection: Optional[str] = Field(None, max_length=100)
    card_number: Optional[str] = Field(None, max_length=50)
    card_finish: Optional[str] = Field(None, max_length=50)
    article_id: Optional[int] = None
    vinted_item_id: Optional[int] = None
    images: Optional[List[str]] = None
    notes: Optional[str] = None


class InventoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lot_id: int
    lot_code: Optional[str] = None
    lot_title: Optional[str] = None

    title: str
    description: Optional[str]
    cost: Optional[Decimal]

    sold_date: Optional[date]
    sold_by: Optional[str]
    sold_platform: Optional[str]
    sale_price: Optional[Decimal]
    fee_amount: Optional[Decimal]
    shipping_cost: Optional[Decimal]

    status: InventoryItemStatusLiteral
    quantity: int
    quantity_sold: int

    category_id: Optional[int]
    category: Optional[CategoryResponse] = None
    parent_category: Optional[CategoryResponse] = None

    card_collection: Optional[str]
    card_number: Optional[str]
    card_finish: Optional[str]

    article_id: Optional[int]
    vinted_item_id: Optional[int]
    images: List[str] = Field(default_factory=list)
    notes: Optional[str]

    net_revenue: Optional[Decimal] = None
    profit: Optional[Decimal] = None
    immobilizzato: Optional[Decimal] = None
    ancora_disponibile: bool = True

    created_at: str
    updated_at: str


class InventoryListResponse(BaseModel):
    items: List[InventoryItemResponse]
    total: int
    total_cost: Decimal = Decimal("0")
    total_revenue: Decimal = Decimal("0")
    total_profit: Decimal = Decimal("0")
    total_immobilizzato: Decimal = Decimal("0")


class PublishToSiteRequest(BaseModel):
    """Opzioni publish. Per ora vuoto (futuro: override fields)."""
    pass


class StatusUpdateRequest(BaseModel):
    """Cambio status manuale (es. mark RESERVED)."""
    status: InventoryItemStatusLiteral


class InventoryImageAdd(BaseModel):
    url: str = Field(..., min_length=1, max_length=2000)


class InventoryImageReorder(BaseModel):
    images: List[str] = Field(..., description="Nuovo ordine — deve essere una permutazione della lista corrente")
