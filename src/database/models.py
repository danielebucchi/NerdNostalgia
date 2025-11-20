"""
Modelli del database per NerdNostalgia.
"""
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Text,
    ForeignKey,
    Enum as SQLEnum,
    Boolean,
    DECIMAL,
)
from sqlalchemy.orm import declarative_base, relationship, Session
import enum


Base = declarative_base()


class UserRole(enum.Enum):
    """Ruoli utente."""
    ADMIN = "admin"
    USER = "user"


class ItemCondition(enum.Enum):
    """Condizioni articolo."""
    NEW = "new"
    USED = "used"
    REFURBISHED = "refurbished"
    FOR_PARTS = "for_parts"


class ListingStatus(enum.Enum):
    """Stati listing."""
    DRAFT = "draft"
    ACTIVE = "active"
    SOLD = "sold"
    ENDED = "ended"
    ERROR = "error"


class User(Base):
    """Modello utente."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    items = relationship("Item", back_populates="user", cascade="all, delete-orphan")
    listings = relationship("Listing", back_populates="user")

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"


class Item(Base):
    """Modello articolo - versione database del models.item.Item."""
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Campi base
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    category = Column(String(100), nullable=False, index=True)
    condition = Column(SQLEnum(ItemCondition), nullable=False)

    # Campi opzionali
    sku = Column(String(100), unique=True, index=True)
    brand = Column(String(100))
    images = Column(Text)  # JSON string array
    tags = Column(Text)  # JSON string array
    shipping_weight = Column(Float)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="items")
    listings = relationship("Listing", back_populates="item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Item(id={self.id}, title='{self.title[:30]}...', sku='{self.sku}')>"


class Platform(Base):
    """Modello piattaforma (eBay, Amazon, etc.)."""
    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False, index=True)  # ebay, amazon, subito
    display_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Config specifica piattaforma (JSON)
    config = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    listings = relationship("Listing", back_populates="platform")

    def __repr__(self):
        return f"<Platform(name='{self.name}')>"


class Listing(Base):
    """Modello listing - rappresenta un articolo pubblicato su una piattaforma."""
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # ID sulla piattaforma
    platform_item_id = Column(String(255), nullable=False, index=True)

    # URL del listing
    url = Column(String(500))

    # Stato
    status = Column(SQLEnum(ListingStatus), default=ListingStatus.DRAFT, nullable=False, index=True)

    # Prezzo al momento della pubblicazione (può differire dal prezzo attuale dell'item)
    listed_price = Column(DECIMAL(10, 2), nullable=False)

    # Statistiche
    views_count = Column(Integer, default=0)
    watchers_count = Column(Integer, default=0)

    # Date
    published_at = Column(DateTime)
    ended_at = Column(DateTime)
    sold_at = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    item = relationship("Item", back_populates="listings")
    platform = relationship("Platform", back_populates="listings")
    user = relationship("User", back_populates="listings")
    history = relationship("ListingHistory", back_populates="listing", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Listing(id={self.id}, platform='{self.platform.name}', platform_item_id='{self.platform_item_id}')>"


class ListingHistory(Base):
    """Storico modifiche listing."""
    __tablename__ = "listing_history"

    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False, index=True)

    # Tipo di evento
    event_type = Column(String(50), nullable=False, index=True)  # created, updated, price_changed, sold, ended

    # Dati dell'evento (JSON)
    event_data = Column(Text)

    # Note
    notes = Column(Text)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    listing = relationship("Listing", back_populates="history")

    def __repr__(self):
        return f"<ListingHistory(listing_id={self.listing_id}, event='{self.event_type}')>"


# Indici composti per performance
from sqlalchemy import Index

# Indice per cercare listings attivi per utente e piattaforma
Index('idx_listings_user_platform_status',
      Listing.user_id, Listing.platform_id, Listing.status)

# Indice per cercare articoli per utente e categoria
Index('idx_items_user_category',
      Item.user_id, Item.category)

# Indice per cercare history per listing e tipo evento
Index('idx_history_listing_event',
      ListingHistory.listing_id, ListingHistory.event_type)
