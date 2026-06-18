"""
Modelli SQLAlchemy per la sync Vinted.
"""
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class VintedSettings(BaseModel):
    __tablename__ = "vinted_settings"

    vinted_user_id = Column(BigInteger, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    sync_hour = Column(Integer, nullable=False, default=4)
    last_run_at = Column(DateTime)


class VintedCategoryMapping(BaseModel):
    __tablename__ = "vinted_category_mappings"

    vinted_catalog_id = Column(Integer, nullable=False, unique=True)
    vinted_catalog_name = Column(String(200), nullable=False)
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    enabled = Column(Boolean, nullable=False, default=True)

    category = relationship("Category", foreign_keys=[category_id])


class VintedSyncLog(BaseModel):
    __tablename__ = "vinted_sync_logs"

    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)
    triggered_by = Column(String(20), nullable=False, default="cron")
    items_fetched = Column(Integer, nullable=False, default=0)
    items_imported = Column(Integer, nullable=False, default=0)
    items_updated = Column(Integer, nullable=False, default=0)
    items_skipped = Column(Integer, nullable=False, default=0)
    error_message = Column(Text)

    # BaseModel has its own created_at/updated_at: started_at è il momento del run
