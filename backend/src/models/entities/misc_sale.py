"""
Entities Pydantic per le vendite generiche.
"""
from datetime import date
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


MiscSaleKindLiteral = Literal["external", "creation"]


class MiscSaleCreate(BaseModel):
    sale_date: Optional[date] = None
    item: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)
    seller: Optional[str] = Field(None, max_length=20)
    platform: Optional[str] = Field(None, max_length=50)
    paid_by_buyer: bool = True
    note: Optional[str] = Field(None, max_length=255)
    kind: MiscSaleKindLiteral = "external"
    material_cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)


class MiscSaleUpdate(BaseModel):
    sale_date: Optional[date] = None
    item: Optional[str] = Field(None, min_length=1, max_length=255)
    amount: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    seller: Optional[str] = Field(None, max_length=20)
    platform: Optional[str] = Field(None, max_length=50)
    paid_by_buyer: Optional[bool] = None
    note: Optional[str] = Field(None, max_length=255)
    kind: Optional[MiscSaleKindLiteral] = None
    material_cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)


class MiscSaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sale_date: Optional[date]
    item: str
    amount: Decimal
    seller: Optional[str]
    platform: Optional[str]
    paid_by_buyer: bool
    note: Optional[str]
    kind: MiscSaleKindLiteral
    material_cost: Optional[Decimal]
    created_at: str
    updated_at: str


class MiscSaleListResponse(BaseModel):
    items: List[MiscSaleResponse]
    total: int
    total_amount: Decimal
    total_paid: Decimal
    total_unpaid: Decimal
    total_material_cost: Decimal = Decimal("0")
    by_kind: dict[str, Decimal] = Field(default_factory=dict)
