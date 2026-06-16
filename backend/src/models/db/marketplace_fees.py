"""
Modello MarketplaceFee per SQLAlchemy.
"""
from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from .base import BaseModel


class MarketplaceFee(BaseModel):
    __tablename__ = "marketplace_fees"

    marketplace = Column(String(50), nullable=False, index=True)
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    markup_percent = Column(Numeric(5, 2), nullable=False)
    note = Column(String(255))

    category = relationship("Category", foreign_keys=[category_id])

    def __repr__(self):
        cat = self.category_id if self.category_id is not None else "default"
        return f"<MarketplaceFee({self.marketplace}/{cat}: +{self.markup_percent}%)>"
