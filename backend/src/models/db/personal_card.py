"""
Modello PersonalCard: carte "sciolte" (no flipping).

Use case: carte comprate al kg (costo bulk) e rivendute singolarmente.
Diverso dal flipping standard (Lotti) perche' qui non c'e' un Lot
strutturato: ogni carta vive a se' stante, con costo eventualmente
medio rispetto al bulk_source e con i propri campi vendita.
"""
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)

from sqlalchemy.orm import relationship

from .base import BaseModel


class PersonalCardStatus:
    IN_STOCK = "IN_STOCK"
    RESERVED = "RESERVED"
    SOLD = "SOLD"
    ARCHIVED = "ARCHIVED"


class PersonalCard(BaseModel):
    __tablename__ = "personal_cards"
    __table_args__ = (
        CheckConstraint(
            "status IN ('IN_STOCK','RESERVED','SOLD','ARCHIVED')",
            name="personal_cards_status_check",
        ),
    )

    name = Column(String(200), nullable=False)
    collection = Column(String(100), index=True)
    card_number = Column(String(50))
    finish = Column(String(50))
    language = Column(String(20), default="IT")
    condition = Column(String(20))
    grading = Column(String(20))

    owned_by = Column(String(20), index=True)
    quantity = Column(Integer, nullable=False, default=1)

    # Acquisto (puo' essere parte di un bulk al kg)
    purchase_date = Column(Date, index=True)
    purchase_cost = Column(Numeric(10, 2))
    purchase_source = Column(String(50))
    bulk_source = Column(String(100))

    # Stima valore (per assicurazione / pricing pre-vendita)
    estimated_value = Column(Numeric(10, 2))
    estimated_value_updated_at = Column(Date)

    # Vendita singola
    status = Column(String(20), nullable=False, default=PersonalCardStatus.IN_STOCK, index=True)
    sold_date = Column(Date, index=True)
    sold_by = Column(String(20))
    sold_platform = Column(String(50))
    sale_price = Column(Numeric(10, 2))
    fee_amount = Column(Numeric(10, 2))
    shipping_cost = Column(Numeric(10, 2))

    images = Column(JSON, nullable=False, default=list)
    notes = Column(Text)

    # ── Scanner: la carta abbinata al catalogo CardTrader ──
    game_id = Column(Integer)
    # Il codice cosi' com'e' stampato ("025/165", "LOB-EN001"): e' quello
    # che i compratori cercano su eBay, e serve nel CSV.
    printed_code = Column(String(50))
    cardtrader_blueprint_id = Column(BigInteger, index=True)
    cardtrader_expansion_id = Column(Integer)
    reverse = Column(Boolean, nullable=False, default=False)
    first_edition = Column(Boolean, nullable=False, default=False)

    # Prezzi di mercato (ultima valutazione) e prezzo a cui la si mette in
    # vendita. estimated_value tiene il SUGGERITO; list_price e' la scelta.
    cardtrader_price = Column(Numeric(10, 2))
    cardtrader_offers = Column(Integer)
    ebay_sold_avg = Column(Numeric(10, 2))
    ebay_sold_count = Column(Integer)
    ebay_sold = Column(JSON)  # [{title, price, date, url}] le vendite usate per la media
    ebay_sold_source = Column(String(20))  # api / manuale
    prices_updated_at = Column(DateTime)
    list_price = Column(Numeric(10, 2))
    # Prezzo diverso per piattaforma (None = calcolato: CardTrader come il
    # sito, eBay con le commissioni e il minimo di 1 euro).
    list_price_cardtrader = Column(Numeric(10, 2))
    list_price_ebay = Column(Numeric(10, 2))

    # Inserzioni
    cardtrader_product_id = Column(BigInteger)
    cardtrader_synced_at = Column(DateTime)
    ebay_sku = Column(String(50))
    ebay_offer_id = Column(String(30))
    ebay_listing_id = Column(String(30))
    # Inserzione con varianti di cui la carta e' una voce (None = da sola).
    ebay_group_key = Column(String(50), index=True)
    ebay_synced_at = Column(DateTime)
    # Articolo del sito (vetrina) con cui la carta e' in vendita anche li'.
    # Gli ordini passano dagli articoli: la carta ne ha uno solo, che si
    # ripubblica invece di duplicarlo.
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="SET NULL"), index=True)
    article = relationship("Article", foreign_keys=[article_id])

    def __repr__(self):
        return (
            f"<PersonalCard(id={self.id}, name='{self.name}', "
            f"status='{self.status}')>"
        )
