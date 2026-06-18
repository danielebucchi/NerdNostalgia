"""
Entities Pydantic per Expense (spese generiche).
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ExpenseCreate(BaseModel):
    spend_date: date
    item: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=50)
    amount: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)
    paid_by: Optional[str] = Field(None, max_length=20)
    related_to_cards: bool = False
    related_to_creations: bool = False
    note: Optional[str] = None


class ExpenseUpdate(BaseModel):
    spend_date: Optional[date] = None
    item: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=50)
    amount: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    paid_by: Optional[str] = Field(None, max_length=20)
    related_to_cards: Optional[bool] = None
    related_to_creations: Optional[bool] = None
    note: Optional[str] = None


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    spend_date: date
    item: str
    category: Optional[str]
    amount: Decimal
    paid_by: Optional[str]
    related_to_cards: bool
    related_to_creations: bool
    note: Optional[str]
    created_at: str
    updated_at: str


class ExpenseListResponse(BaseModel):
    items: List[ExpenseResponse]
    total: int
    total_amount: Decimal = Decimal("0")
    total_card_related: Decimal = Decimal("0")
    total_creation_related: Decimal = Decimal("0")
    by_category: dict[str, Decimal] = Field(default_factory=dict)
