"""
Modello MarketplaceFee per SQLAlchemy.
"""
from sqlalchemy import Column, Numeric, String

from .base import BaseModel


class MarketplaceFee(BaseModel):
    __tablename__ = "marketplace_fees"

    marketplace = Column(String(50), nullable=False, index=True)
    category = Column(String(100))
    markup_percent = Column(Numeric(5, 2), nullable=False)
    note = Column(String(255))

    def __repr__(self):
        cat = self.category or "default"
        return f"<MarketplaceFee({self.marketplace}/{cat}: +{self.markup_percent}%)>"
