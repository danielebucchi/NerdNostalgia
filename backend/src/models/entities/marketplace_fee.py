"""
Entities Pydantic per marketplace fees.
"""
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MarketplaceFeeCreate(BaseModel):
    marketplace: str = Field(..., min_length=1, max_length=50)
    category: Optional[str] = Field(None, max_length=100)
    markup_percent: Decimal = Field(..., ge=0, le=100, max_digits=5, decimal_places=2)
    note: Optional[str] = Field(None, max_length=255)


class MarketplaceFeeUpdate(BaseModel):
    markup_percent: Optional[Decimal] = Field(
        None, ge=0, le=100, max_digits=5, decimal_places=2
    )
    category: Optional[str] = Field(None, max_length=100)
    note: Optional[str] = Field(None, max_length=255)


class MarketplaceFeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    marketplace: str
    category: Optional[str]
    markup_percent: Decimal
    note: Optional[str]
    created_at: str
    updated_at: str


class MarketplaceFeeListResponse(BaseModel):
    items: List[MarketplaceFeeResponse]
    total: int
