"""
Base SQLAlchemy configuration.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.orm import declarative_base


def _utc_now() -> datetime:
    """Timezone-aware UTC now. Sostituisce datetime.utcnow() (deprecated 3.12+).
    Restituisce naive UTC perche' lo schema usa TIMESTAMP senza timezone."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


Base = declarative_base()


class BaseModel(Base):
    """Classe base per tutti i modelli con campi comuni."""
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(
        DateTime,
        default=_utc_now,
        onupdate=_utc_now,
        nullable=False,
    )

    def to_dict(self):
        """Converte il modello in dizionario."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
