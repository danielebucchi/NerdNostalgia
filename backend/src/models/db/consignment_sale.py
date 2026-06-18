"""
Modello ConsignmentSale: vendite in contovendita.
"""
from sqlalchemy import Boolean, Column, Date, Numeric, String, Text

from .base import BaseModel


class ConsignmentSale(BaseModel):
    __tablename__ = "consignment_sales"

    sale_date = Column(Date, nullable=False, index=True)
    item = Column(String(255), nullable=False)
    consignor = Column(String(100), nullable=False, index=True)
    sale_price = Column(Numeric(10, 2), nullable=False)
    commission_pct = Column(Numeric(5, 2))
    commission_amount = Column(Numeric(10, 2))
    fee_amount = Column(Numeric(10, 2))
    shipping_cost = Column(Numeric(10, 2))
    sold_platform = Column(String(50))
    sold_by = Column(String(20))
    buyer = Column(String(100))
    paid_out = Column(Boolean, nullable=False, default=False, index=True)
    payout_date = Column(Date)
    note = Column(Text)

    def __repr__(self):
        return f"<ConsignmentSale({self.sale_date} {self.item} → {self.consignor} €{self.sale_price})>"
