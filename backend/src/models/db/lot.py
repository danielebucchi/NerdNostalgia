"""
Modello Lot: container di InventoryItem con metadati di acquisto comuni
(data, piattaforma, chi ha comprato, costo totale). Ogni inventory_item
appartiene a esattamente un Lot.
"""
from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class LotStatus:
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class Lot(BaseModel):
    __tablename__ = "lots"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN','CLOSED','ARCHIVED')",
            name="lots_status_check",
        ),
    )

    code = Column(String(20), unique=True, nullable=False)
    title = Column(String(200))
    purchase_date = Column(Date, index=True)
    purchase_platform = Column(String(50))
    bought_by = Column(String(20))
    total_cost = Column(Numeric(10, 2))
    notes = Column(Text)
    status = Column(String(20), nullable=False, default=LotStatus.OPEN, index=True)

    items = relationship(
        "InventoryItem",
        back_populates="lot",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Lot(id={self.id}, code='{self.code}', title='{self.title}')>"
