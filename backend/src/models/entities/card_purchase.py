"""
Entities Pydantic per le spese carte all'ingrosso.
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CardPurchaseCreate(BaseModel):
    purchase_date: Optional[date] = None
    item: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)
    note: Optional[str] = Field(None, max_length=255)


class CardPurchaseUpdate(BaseModel):
    purchase_date: Optional[date] = None
    item: Optional[str] = Field(None, min_length=1, max_length=255)
    amount: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    note: Optional[str] = Field(None, max_length=255)


class CardPurchaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purchase_date: Optional[date]
    item: str
    amount: Decimal
    note: Optional[str]
    created_at: str
    updated_at: str


class CardPurchaseListResponse(BaseModel):
    items: List[CardPurchaseResponse]
    total: int
    total_amount: Decimal
