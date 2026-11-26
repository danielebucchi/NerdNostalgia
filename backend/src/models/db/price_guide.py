"""
La guida prezzi pubblica delle carte Pokémon: set e carte con il prezzo
CardTrader piu' basso, aggiornati ogni settimana (utils/price_guide.py).
"""
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class PriceGuideSet(Base):
    __tablename__ = "price_guide_sets"

    id = Column(Integer, primary_key=True)            # id dell'espansione CardTrader
    slug = Column(String(120), nullable=False, unique=True)
    name_en = Column(String(200), nullable=False)
    name_it = Column(String(200))
    tcgdex_id = Column(String(40))
    release_date = Column(String(10))
    card_count = Column(Integer)
    serie = Column(String(120))
    logo_url = Column(String(500))
    updated_at = Column(DateTime, nullable=False)

    cards = relationship("PriceGuideCard", back_populates="set", cascade="all, delete-orphan")

    @property
    def nome(self) -> str:
        return self.name_it or self.name_en


class PriceGuideCard(Base):
    __tablename__ = "price_guide_cards"

    id = Column(Integer, primary_key=True)
    set_id = Column(Integer, ForeignKey("price_guide_sets.id", ondelete="CASCADE"), nullable=False, index=True)
    blueprint_id = Column(Integer, nullable=False, unique=True)
    number = Column(String(20), nullable=False)
    slug = Column(String(160), nullable=False)
    name_en = Column(String(200), nullable=False)
    name_it = Column(String(200))
    image_url = Column(String(500))
    min_price_cents = Column(Integer)
    offers = Column(Integer, nullable=False, default=0)
    # {"it": {"NM": centesimi, "SP": ..., ...}, "en": {...}}: il prezzo piu'
    # basso per condizione e lingua (utils/price_guide.py).
    prices = Column(JSON)
    updated_at = Column(DateTime, nullable=False)

    set = relationship("PriceGuideSet", back_populates="cards")

    @property
    def nome(self) -> str:
        return self.name_it or self.name_en
