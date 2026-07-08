"""
Modello Setting: config runtime chiave/valore.

Niente BaseModel: la PK e' `key` (stringa), non id autoincrement, e non
serve created_at. La whitelist delle chiavi pubbliche sta in api/settings.py.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text

from .base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)

    def __repr__(self):
        return f"<Setting(key='{self.key}', value='{str(self.value)[:40]}')>"
