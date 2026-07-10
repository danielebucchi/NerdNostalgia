"""
Entities Pydantic per Lot.
"""
from datetime import date
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


LotStatusLiteral = Literal["OPEN", "CLOSED", "ARCHIVED"]


class LotCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    purchase_date: Optional[date] = None
    purchase_platform: Optional[str] = Field(None, max_length=50)
    bought_by: Optional[str] = Field(None, max_length=20)
    total_cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    notes: Optional[str] = None
    status: LotStatusLiteral = "OPEN"


class LotUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    purchase_date: Optional[date] = None
    purchase_platform: Optional[str] = Field(None, max_length=50)
    bought_by: Optional[str] = Field(None, max_length=20)
    total_cost: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    notes: Optional[str] = None
    status: Optional[LotStatusLiteral] = None


class LotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    title: Optional[str]
    purchase_date: Optional[date]
    purchase_platform: Optional[str]
    bought_by: Optional[str]
    total_cost: Optional[Decimal]
    notes: Optional[str]
    status: LotStatusLiteral

    # KPI aggregati (computed)
    items_count: int = 0
    quantity_total: int = 0
    quantity_sold: int = 0
    cost_sum: Decimal = Decimal("0")
    revenue_sum: Decimal = Decimal("0")
    profit_sum: Decimal = Decimal("0")
    immobilizzato: Decimal = Decimal("0")
    status_breakdown: dict[str, int] = Field(default_factory=dict)

    created_at: str
    updated_at: str


class LotListResponse(BaseModel):
    items: List[LotResponse]
    total: int


class DistributeLotCostRequest(BaseModel):
    """Distribuisce total_cost del Lot su tutti gli item (pesato per qty)."""
    total_cost: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)


class DistributeLotCostResponse(BaseModel):
    lot_id: int
    items_updated: int
    total_pieces: int
    unit_cost: Decimal


class BulkPublishRequest(BaseModel):
    """Crea Article per la lista di item_id selezionati nel Lot."""
    item_ids: List[int] = Field(..., min_length=1)
    # False = bozze DRAFT; True = direttamente PUBLISHED sul catalogo.
    publish_now: bool = False


class BulkPublishResponse(BaseModel):
    created: int
    skipped: int
    item_ids_created: List[int]


class DuplicateLotRequest(BaseModel):
    """Clona un lotto esistente. Il nuovo lotto parte in stato OPEN e riceve
    un nuovo code sequenziale. Foto e status di vendita degli item NON vengono
    copiati (il duplicato serve da template)."""
    copy_items: bool = True
    title_prefix: str = Field(
        "Copia di ",
        max_length=32,
        description="Prefisso applicato al titolo del nuovo lotto",
    )
