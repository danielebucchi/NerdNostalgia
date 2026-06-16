"""
Entities Pydantic per gli articoli.
"""
import enum
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


class ArticleCreate(BaseModel):
    user_id: int = Field(..., description="ID utente proprietario")
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)
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


class ArticleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
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


class ArticleImageAdd(BaseModel):
    url: str = Field(..., min_length=1, description="URL dell'immagine da aggiungere")


class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    description: Optional[str]
    price: Decimal
    currency: str
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
