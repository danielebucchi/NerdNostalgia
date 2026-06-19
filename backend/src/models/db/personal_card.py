"""
Modello PersonalCard: carte "sciolte" (no flipping).

Use case: carte comprate al kg (costo bulk) e rivendute singolarmente.
Diverso dal flipping standard (Lotti) perche' qui non c'e' un Lot
strutturato: ogni carta vive a se' stante, con costo eventualmente
medio rispetto al bulk_source e con i propri campi vendita.
"""
from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)

from .base import BaseModel


class PersonalCardStatus:
    IN_STOCK = "IN_STOCK"
    RESERVED = "RESERVED"
    SOLD = "SOLD"
    ARCHIVED = "ARCHIVED"


class PersonalCard(BaseModel):
    __tablename__ = "personal_cards"
    __table_args__ = (
        CheckConstraint(
            "status IN ('IN_STOCK','RESERVED','SOLD','ARCHIVED')",
            name="personal_cards_status_check",
        ),
    )

    name = Column(String(200), nullable=False)
    collection = Column(String(100), index=True)
    card_number = Column(String(50))
    finish = Column(String(50))
    language = Column(String(20), default="IT")
    condition = Column(String(20))
    grading = Column(String(20))

    owned_by = Column(String(20), index=True)
    quantity = Column(Integer, nullable=False, default=1)

    # Acquisto (puo' essere parte di un bulk al kg)
    purchase_date = Column(Date, index=True)
    purchase_cost = Column(Numeric(10, 2))
    purchase_source = Column(String(50))
    bulk_source = Column(String(100))

    # Stima valore (per assicurazione / pricing pre-vendita)
    estimated_value = Column(Numeric(10, 2))
    estimated_value_updated_at = Column(Date)

    # Vendita singola
    status = Column(String(20), nullable=False, default=PersonalCardStatus.IN_STOCK, index=True)
    sold_date = Column(Date, index=True)
    sold_by = Column(String(20))
    sold_platform = Column(String(50))
    sale_price = Column(Numeric(10, 2))
    fee_amount = Column(Numeric(10, 2))
    shipping_cost = Column(Numeric(10, 2))

    images = Column(JSON, nullable=False, default=list)
    notes = Column(Text)

    def __repr__(self):
        return (
            f"<PersonalCard(id={self.id}, name='{self.name}', "
            f"status='{self.status}')>"
        )
