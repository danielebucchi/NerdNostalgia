"""
Recensione del venditore, legata a un ordine.
"""
import enum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import Enum as PgEnum
from sqlalchemy.orm import relationship

from .base import BaseModel


class ReviewStatus(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Review(BaseModel):
    __tablename__ = "reviews"

    # UNIQUE: chi ha comprato una volta scrive una volta. E' anche la prova
    # che la recensione nasce da un acquisto vero.
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # NULL per chi ha comprato da ospite: si recensisce con il link ricevuto
    # via email, senza account.
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Copiato dall'ordine: resta leggibile anche se l'account sparisce
    author_name = Column(String(255), nullable=False)
    rating = Column(Integer, nullable=False)
    body = Column(Text)

    status = Column(
        PgEnum(ReviewStatus, name="review_status", create_type=False),
        nullable=False,
        default=ReviewStatus.PENDING,
        index=True,
    )
    # Risposta pubblica del venditore
    reply = Column(Text)
    moderated_at = Column(DateTime)

    order = relationship("Order")

    def __repr__(self):
        return f"<Review(order={self.order_id}, {self.rating}★, {self.status})>"
