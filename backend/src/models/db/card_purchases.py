"""
Modello CardPurchase per SQLAlchemy.
Spese carte all'ingrosso (bustine, lotti) — clona il foglio "Spese carte".
"""
from sqlalchemy import Column, Date, Numeric, String

from .base import BaseModel


class CardPurchase(BaseModel):
    __tablename__ = "card_purchases"

    purchase_date = Column(Date, index=True)
    item = Column(String(255), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    note = Column(String(255))

    def __repr__(self):
        return f"<CardPurchase({self.purchase_date} {self.item} €{self.amount})>"
