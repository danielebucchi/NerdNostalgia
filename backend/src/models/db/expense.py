"""
Modello Expense: spese generiche (foglio Spese).

Diverso da CardPurchase (foglio "Spese carte"): qui ci sono tutte le
spese non riconducibili a un acquisto bulk di carte (es. spedizioni,
materiali, fee account, viaggi). Una expense puo' essere marcata come
'related_to_cards=True' per impattare il profitto netto delle carte
sciolte.
"""
from sqlalchemy import Boolean, Column, Date, Numeric, String, Text

from .base import BaseModel


class Expense(BaseModel):
    __tablename__ = "expenses"

    spend_date = Column(Date, nullable=False, index=True)
    item = Column(String(255), nullable=False)
    category = Column(String(50), index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    paid_by = Column(String(20))
    related_to_cards = Column(Boolean, nullable=False, default=False, index=True)
    related_to_creations = Column(Boolean, nullable=False, default=False, index=True)
    note = Column(Text)

    def __repr__(self):
        return f"<Expense({self.spend_date} {self.item} €{self.amount})>"
