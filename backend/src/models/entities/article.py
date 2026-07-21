"""
Entities Pydantic per gli articoli.
"""
import enum
from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict

from models.entities.category import CategoryResponse


class ArticleCondition(str, enum.Enum):
    NEW = "NEW"
    USED = "USED"
    REFURBISHED = "REFURBISHED"
    FOR_PARTS = "FOR_PARTS"


class ArticleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    SOLD = "SOLD"
    ARCHIVED = "ARCHIVED"


class VintedStatus(str, enum.Enum):
    NOT_LISTED = "NOT_LISTED"
    LISTED = "LISTED"
    SOLD = "SOLD"


class EbayStatus(str, enum.Enum):
    NOT_LISTED = "NOT_LISTED"
    LISTED = "LISTED"
    SOLD = "SOLD"


class ArticleInventoryFields(BaseModel):
    """Campi inventario condivisi tra Create e Update."""
    lotto: Optional[str] = Field(None, max_length=50)
    purchase_date: Optional[date] = None
    cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    purchase_platform: Optional[str] = Field(None, max_length=50)
    bought_by: Optional[str] = Field(None, max_length=20)
    sold_by: Optional[str] = Field(None, max_length=20)
    fee_amount: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    shipping_cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    quantity_sold: Optional[int] = Field(None, ge=0)
    card_collection: Optional[str] = Field(None, max_length=100)
    card_number: Optional[str] = Field(None, max_length=50)
    card_finish: Optional[str] = Field(None, max_length=50)
    card_condition: Optional[str] = Field(None, max_length=30)
    card_language: Optional[str] = Field(None, max_length=5)
    card_reverse: Optional[bool] = None
    card_first_edition: Optional[bool] = None


class ArticleCreate(ArticleInventoryFields):
    user_id: int = Field(..., description="ID utente proprietario")
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)
    shipping_price: Optional[Decimal] = Field(
        Decimal("5.00"), ge=0, max_digits=10, decimal_places=2,
        description="Costo spedizione richiesto al cliente. Default 5€.",
    )
    currency: str = Field("EUR", min_length=3, max_length=3)
    category_id: Optional[int] = Field(None, description="FK categoria/sottocategoria")
    condition: ArticleCondition = ArticleCondition.USED
    status: ArticleStatus = ArticleStatus.DRAFT
    quantity: int = Field(1, ge=0)
    sku: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    weight_kg: Optional[Decimal] = Field(None, ge=0, max_digits=8, decimal_places=2)
    dimensions_cm: Optional[str] = Field(None, max_length=50)
    images: List[str] = Field(default_factory=list)
    article_metadata: dict = Field(default_factory=dict)


class ArticleUpdate(ArticleInventoryFields):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    shipping_price: Optional[Decimal] = Field(
        None, ge=0, max_digits=10, decimal_places=2,
        description="Costo spedizione richiesto al cliente",
    )
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    category_id: Optional[int] = None
    condition: Optional[ArticleCondition] = None
    status: Optional[ArticleStatus] = None
    quantity: Optional[int] = Field(None, ge=0)
    sku: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    weight_kg: Optional[Decimal] = Field(None, ge=0, max_digits=8, decimal_places=2)
    dimensions_cm: Optional[str] = Field(None, max_length=50)
    images: Optional[List[str]] = None
    article_metadata: Optional[dict] = None
    cardtrader_blueprint_id: Optional[int] = Field(
        None, description="Blueprint CardTrader abbinato (None = scollega)"
    )


class ArticleImageAdd(BaseModel):
    url: str = Field(..., min_length=1, description="URL dell'immagine da aggiungere")


class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    description: Optional[str]
    price: Decimal
    shipping_price: Optional[Decimal] = None
    currency: str
    # Inventory fields
    lotto: Optional[str] = None
    purchase_date: Optional[date] = None
    cost: Optional[Decimal] = None
    purchase_platform: Optional[str] = None
    bought_by: Optional[str] = None
    sold_by: Optional[str] = None
    fee_amount: Optional[Decimal] = None
    shipping_cost: Optional[Decimal] = None
    quantity_sold: int = 0
    card_collection: Optional[str] = None
    card_number: Optional[str] = None
    card_finish: Optional[str] = None
    card_condition: Optional[str] = None
    card_language: Optional[str] = None
    card_reverse: bool = False
    card_first_edition: bool = False
    # Derived (calcolati in _to_response)
    net_revenue: Optional[Decimal] = None
    profit: Optional[Decimal] = None
    immobilizzato: Optional[Decimal] = None
    # Categoria
    category_id: Optional[int] = None
    category: Optional[CategoryResponse] = None
    parent_category: Optional[CategoryResponse] = None
    condition: ArticleCondition
    status: ArticleStatus
    quantity: int
    sku: Optional[str]
    brand: Optional[str]
    model: Optional[str]
    weight_kg: Optional[Decimal]
    dimensions_cm: Optional[str]
    images: List[str]
    article_metadata: dict
    display_order: int = 0
    vinted_status: VintedStatus = VintedStatus.NOT_LISTED
    vinted_url: Optional[str] = None
    vinted_synced_at: Optional[str] = None
    vinted_price: Optional[Decimal] = None
    ebay_status: EbayStatus = EbayStatus.NOT_LISTED
    ebay_url: Optional[str] = None
    ebay_synced_at: Optional[str] = None
    ebay_price: Optional[Decimal] = None
    cardtrader_blueprint_id: Optional[int] = None
    cardtrader_product_id: Optional[int] = None
    cardtrader_synced_at: Optional[str] = None
    created_at: str
    updated_at: str
    published_at: Optional[str]
    sold_at: Optional[str]


class ArticleListResponse(BaseModel):
    items: List[ArticleResponse]
    total: int
    skip: int
    limit: int


class ReorderRequest(BaseModel):
    order: List[int] = Field(..., min_length=1)


class VintedSyncUpdate(BaseModel):
    vinted_status: VintedStatus
    vinted_url: Optional[str] = Field(None, max_length=500)
    vinted_price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)


class EbaySyncUpdate(BaseModel):
    ebay_status: EbayStatus
    ebay_url: Optional[str] = Field(None, max_length=500)
    ebay_price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
