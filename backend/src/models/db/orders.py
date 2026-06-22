"""
Modelli Order + OrderItem per SQLAlchemy.

Pagamento out-of-band (paypal.me): l'ordine parte come PENDING quando
il compratore compila il form e diventa PAID solo via conferma admin.
"""
import enum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import Enum as PgEnum
from sqlalchemy.orm import relationship

from .base import BaseModel


class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CANCELLED = "CANCELLED"


class Order(BaseModel):
    __tablename__ = "orders"

    # Buyer
    buyer_name = Column(String(255), nullable=False)
    buyer_email = Column(String(255), nullable=False, index=True)
    buyer_phone = Column(String(50))

    # Shipping address
    ship_street = Column(String(255), nullable=False)
    ship_city = Column(String(120), nullable=False)
    ship_postal_code = Column(String(20), nullable=False)
    ship_province = Column(String(120))
    ship_country = Column(String(80), nullable=False, default="Italia")

    # Pricing (snapshot al checkout)
    subtotal = Column(Numeric(10, 2), nullable=False)
    shipping_total = Column(Numeric(10, 2), nullable=False)
    grand_total = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="EUR")

    notes = Column(Text)
    status = Column(
        PgEnum(OrderStatus, name="order_status", create_type=False),
        nullable=False,
        default=OrderStatus.PENDING,
        index=True,
    )
    paid_at = Column(DateTime)
    shipped_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    admin_notes = Column(Text)

    ip_address = Column(String(45))

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class OrderItem(BaseModel):
    __tablename__ = "order_items"

    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id = Column(
        Integer,
        ForeignKey("articles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title_snapshot = Column(String(255), nullable=False)
    price_snapshot = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)

    order = relationship("Order", back_populates="items")
    article = relationship("Article", foreign_keys=[article_id])
