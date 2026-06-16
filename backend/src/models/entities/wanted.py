"""
Entities Pydantic per la sezione cerco/compro.
"""
import enum
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from models.entities.article import ArticleCondition


class WantedStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    FULFILLED = "FULFILLED"
    CLOSED = "CLOSED"


class WantedItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    preferred_condition: Optional[ArticleCondition] = None
    max_price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    currency: str = Field("EUR", min_length=3, max_length=3)
    notes: Optional[str] = None
    priority: int = Field(0, ge=0, le=100)
    status: WantedStatus = WantedStatus.ACTIVE


class WantedItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    preferred_condition: Optional[ArticleCondition] = None
    max_price: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    notes: Optional[str] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    status: Optional[WantedStatus] = None


class WantedItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str]
    category: Optional[str]
    brand: Optional[str]
    model: Optional[str]
    preferred_condition: Optional[ArticleCondition]
    max_price: Optional[Decimal]
    currency: str
    notes: Optional[str]
    priority: int
    status: WantedStatus
    created_at: str
    updated_at: str
    fulfilled_at: Optional[str]


class WantedItemListResponse(BaseModel):
    items: List[WantedItemResponse]
    total: int
    skip: int
    limit: int
