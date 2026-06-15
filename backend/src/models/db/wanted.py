"""
Modello WantedItem per SQLAlchemy.
"""
import enum

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy import Enum as PgEnum

from .articles import ArticleCondition
from .base import BaseModel


class WantedStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    FULFILLED = "FULFILLED"
    CLOSED = "CLOSED"


class WantedItem(BaseModel):
    __tablename__ = "wanted_items"

    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)
    brand = Column(String(100))
    model = Column(String(100))

    preferred_condition = Column(
        PgEnum(ArticleCondition, name="article_condition", create_type=False),
        nullable=True,
    )

    max_price = Column(Numeric(10, 2))
    currency = Column(String(3), default="EUR")
    notes = Column(Text)

    status = Column(
        PgEnum(WantedStatus, name="wanted_status", create_type=False),
        nullable=False,
        default=WantedStatus.ACTIVE,
        index=True,
    )

    priority = Column(Integer, nullable=False, default=0)
    fulfilled_at = Column(DateTime)

    def __repr__(self):
        return (
            f"<WantedItem(id={self.id}, title='{self.title}', "
            f"status='{self.status.value if self.status else None}')>"
        )
