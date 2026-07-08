"""
Modello CategoryAlert: iscrizione email agli avvisi nuovi arrivi.

category_id NULL = iscritto a TUTTE le categorie. Nessun updated_at nello
schema (una riga o esiste o viene cancellata), quindi niente BaseModel.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CategoryAlert(Base):
    __tablename__ = "category_alerts"
    __table_args__ = (
        UniqueConstraint("email", "category_id", name="uq_category_alerts_email_cat"),
    )

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False)
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime, default=_utc_now, nullable=False)

    category = relationship("Category", foreign_keys=[category_id])

    def __repr__(self):
        return f"<CategoryAlert(email='{self.email}', category_id={self.category_id})>"
