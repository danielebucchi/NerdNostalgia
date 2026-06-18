"""
Modello MiscSale per SQLAlchemy.
Vendite generiche di articoli senza scheda nel catalogo — clona "Vendite".
"""
from sqlalchemy import Boolean, Column, Date, Numeric, String

from .base import BaseModel


class MiscSale(BaseModel):
    __tablename__ = "misc_sales"

    sale_date = Column(Date, index=True)
    item = Column(String(255), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    seller = Column(String(20), index=True)
    platform = Column(String(50))
    paid_by_buyer = Column(Boolean, nullable=False, default=True)
    note = Column(String(255))

    def __repr__(self):
        return f"<MiscSale({self.sale_date} {self.item} €{self.amount} {self.platform})>"
