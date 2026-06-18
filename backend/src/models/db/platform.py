"""
Modello Platform: piattaforme unificate per acquisti e vendite.
"""
from sqlalchemy import Boolean, Column, Integer, String, Text

from .base import BaseModel


class Platform(BaseModel):
    __tablename__ = "platforms"

    name = Column(String(50), nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    icon = Column(String(10))
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    note = Column(Text)

    def __repr__(self):
        return f"<Platform(id={self.id}, name='{self.name}', active={self.is_active})>"
