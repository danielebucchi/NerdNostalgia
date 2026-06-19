"""
Modello Article per SQLAlchemy.
"""
from sqlalchemy import BigInteger, Column, String, Integer, Numeric, Text, Enum, Date, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from .base import BaseModel


class ArticleCondition(enum.Enum):
    """Condizioni articolo."""
    NEW = "NEW"
    USED = "USED"
    REFURBISHED = "REFURBISHED"
    FOR_PARTS = "FOR_PARTS"


class ArticleStatus(enum.Enum):
    """Stati articolo."""
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    SOLD = "SOLD"
    ARCHIVED = "ARCHIVED"


class VintedStatus(enum.Enum):
    """Stato sincronizzazione con Vinted."""
    NOT_LISTED = "NOT_LISTED"
    LISTED = "LISTED"
    SOLD = "SOLD"


class EbayStatus(enum.Enum):
    """Stato sincronizzazione con eBay."""
    NOT_LISTED = "NOT_LISTED"
    LISTED = "LISTED"
    SOLD = "SOLD"


class Article(BaseModel):
    """
    Modello articolo del sistema.

    Attributes:
        user_id: ID utente proprietario
        title: Titolo/nome dell'articolo
        description: Descrizione dettagliata
        price: Prezzo di vendita
        currency: Valuta (EUR, USD, etc)
        category: Categoria prodotto
        condition: Condizione (new, used, refurbished, for_parts)
        status: Stato (draft, published, sold, archived)
        quantity: Quantita' disponibile
        sku: Codice prodotto univoco
        brand: Marca del prodotto
        model: Modello del prodotto
        weight_kg: Peso in chilogrammi
        dimensions_cm: Dimensioni in cm
        images: Array JSON di URL immagini
        article_metadata: Metadati aggiuntivi
        published_at: Data e ora di pubblicazione
        sold_at: Data e ora di vendita
    """
    __tablename__ = "articles"

    # Foreign key
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Campi base
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Pricing
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="EUR")

    # Inventory tracking (clone foglio "Flipping Inventario" / "Carte Pokemon Inventario")
    lotto = Column(String(50), index=True)
    purchase_date = Column(Date, index=True)
    cost = Column(Numeric(10, 2))
    purchase_platform = Column(String(50), index=True)
    bought_by = Column(String(20))
    sold_by = Column(String(20))
    fee_amount = Column(Numeric(10, 2))
    shipping_cost = Column(Numeric(10, 2))
    quantity_sold = Column(Integer, nullable=False, default=0)

    # Campi specifici carte
    card_collection = Column(String(100))
    card_number = Column(String(50))
    card_finish = Column(String(50))

    # Classificazione
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    condition = Column(Enum(ArticleCondition), default=ArticleCondition.USED, nullable=False, index=True)
    status = Column(Enum(ArticleStatus), default=ArticleStatus.DRAFT, nullable=False, index=True)

    # Inventario
    quantity = Column(Integer, default=1, nullable=False)
    sku = Column(String(100), unique=True, index=True)

    # Dettagli prodotto
    brand = Column(String(100))
    model = Column(String(100))
    weight_kg = Column(Numeric(8, 2))
    dimensions_cm = Column(String(50))

    # JSON fields
    images = Column(JSON, default=list)
    article_metadata = Column(JSON, default=dict)

    # Ordinamento manuale del catalogo (piu' basso = prima)
    display_order = Column(Integer, nullable=False, default=0, index=True)

    # Vinted sync (manuale assistito + sync automatica da profilo)
    vinted_status = Column(
        Enum(VintedStatus, name="vinted_status", create_type=False),
        nullable=False,
        default=VintedStatus.NOT_LISTED,
        index=True,
    )
    vinted_url = Column(String(500))
    vinted_synced_at = Column(DateTime)
    vinted_price = Column(Numeric(10, 2))
    vinted_item_id = Column(BigInteger, unique=True)

    # eBay sync (manuale assistito)
    ebay_status = Column(
        Enum(EbayStatus, name="ebay_status", create_type=False),
        nullable=False,
        default=EbayStatus.NOT_LISTED,
        index=True,
    )
    ebay_url = Column(String(500))
    ebay_synced_at = Column(DateTime)
    ebay_price = Column(Numeric(10, 2))

    # Timestamp aggiuntivi
    published_at = Column(DateTime)
    sold_at = Column(DateTime)

    # Relationship
    user = relationship("User", backref="articles")
    category = relationship("Category", foreign_keys=[category_id])

    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title}', status='{self.status.value if self.status else None}')>"

    def to_dict(self, include_user=False):
        """
        Converte l'articolo in dizionario.

        Args:
            include_user: Se includere i dati dell'utente (default: False)

        Returns:
            dict: Dizionario con i dati dell'articolo
        """
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "price": float(self.price) if self.price else None,
            "currency": self.currency,
            "category_id": self.category_id,
            "condition": self.condition.value if self.condition else None,
            "status": self.status.value if self.status else None,
            "quantity": self.quantity,
            "sku": self.sku,
            "brand": self.brand,
            "model": self.model,
            "weight_kg": float(self.weight_kg) if self.weight_kg else None,
            "dimensions_cm": self.dimensions_cm,
            "images": self.images or [],
            "article_metadata": self.article_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "sold_at": self.sold_at.isoformat() if self.sold_at else None,
        }

        if include_user and self.user:
            data["user"] = self.user.to_dict()

        return data

    def mark_as_published(self):
        """Marca l'articolo come pubblicato."""
        self.status = ArticleStatus.PUBLISHED
        if not self.published_at:
            self.published_at = datetime.utcnow()

    def mark_as_sold(self):
        """Marca l'articolo come venduto."""
        self.status = ArticleStatus.SOLD
        if not self.sold_at:
            self.sold_at = datetime.utcnow()

    def mark_as_archived(self):
        """Marca l'articolo come archiviato."""
        self.status = ArticleStatus.ARCHIVED

    def add_image(self, image_url: str):
        """
        Aggiunge un'immagine all'articolo.

        Args:
            image_url: URL dell'immagine da aggiungere
        """
        if not self.images:
            self.images = []
        if image_url not in self.images:
            self.images.append(image_url)

    def remove_image(self, image_url: str):
        """
        Rimuove un'immagine dall'articolo.

        Args:
            image_url: URL dell'immagine da rimuovere
        """
        if self.images and image_url in self.images:
            self.images.remove(image_url)
