"""
Modello InventoryItem.

Ogni item appartiene a un Lot (lot_id NOT NULL). I metadati di acquisto
comuni (data, piattaforma, chi ha comprato, costo totale) vivono sul Lot.
"""
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class InventoryItemStatus:
    DRAFT = "DRAFT"        # catalogato, niente Article
    LINKED = "LINKED"      # Article esiste in stato DRAFT
    LISTED = "LISTED"      # Article PUBLISHED
    RESERVED = "RESERVED"  # in trattativa
    SOLD = "SOLD"
    ARCHIVED = "ARCHIVED"


class InventoryItem(BaseModel):
    __tablename__ = "inventory_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','LINKED','LISTED','RESERVED','SOLD','ARCHIVED')",
            name="inventory_items_status_check",
        ),
    )

    lot_id = Column(
        Integer,
        ForeignKey("lots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    title = Column(String(500), nullable=False)
    description = Column(Text)

    cost = Column(Numeric(10, 2))

    sold_date = Column(Date, index=True)
    sold_by = Column(String(20))
    sold_platform = Column(String(50))
    sale_price = Column(Numeric(10, 2))
    fee_amount = Column(Numeric(10, 2))
    shipping_cost = Column(Numeric(10, 2))

    status = Column(
        String(20),
        nullable=False,
        default=InventoryItemStatus.DRAFT,
        index=True,
    )
    quantity = Column(Integer, nullable=False, default=1)
    quantity_sold = Column(Integer, nullable=False, default=0)

    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    card_collection = Column(String(100))
    card_number = Column(String(50))
    card_finish = Column(String(50))

    article_id = Column(
        Integer,
        ForeignKey("articles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vinted_item_id = Column(BigInteger)

    images = Column(JSON, nullable=False, default=list)
    notes = Column(Text)

    lot = relationship("Lot", back_populates="items")
    category = relationship("Category", foreign_keys=[category_id])
    article = relationship("Article", foreign_keys=[article_id])

    def __repr__(self):
        return (
            f"<InventoryItem(id={self.id}, lot_id={self.lot_id}, "
            f"title='{self.title[:30]}', status='{self.status}')>"
        )
