"""
Modello per rappresentare un articolo da vendere.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from decimal import Decimal


@dataclass
class Item:
    """
    Rappresenta un articolo da pubblicare su una piattaforma e-commerce.
    """
    title: str
    description: str
    price: Decimal
    quantity: int
    category: str
    condition: str  # new, used, refurbished

    # Optional fields
    sku: Optional[str] = None
    brand: Optional[str] = None
    images: List[str] = field(default_factory=list)
    shipping_weight: Optional[float] = None
    shipping_dimensions: Optional[dict] = None

    # Platform-specific IDs (popolati dopo la pubblicazione)
    ebay_id: Optional[str] = None
    amazon_id: Optional[str] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    custom_fields: dict = field(default_factory=dict)

    def __post_init__(self):
        """Validazione dei campi."""
        if self.price <= 0:
            raise ValueError("Il prezzo deve essere maggiore di zero")

        if self.quantity < 0:
            raise ValueError("La quantità non può essere negativa")

        valid_conditions = ["new", "used", "refurbished", "for_parts"]
        if self.condition.lower() not in valid_conditions:
            raise ValueError(
                f"Condizione '{self.condition}' non valida. "
                f"Valori ammessi: {', '.join(valid_conditions)}"
            )

        # Normalizza la condizione
        self.condition = self.condition.lower()

    def to_dict(self) -> dict:
        """Converte l'oggetto in dizionario."""
        return {
            "title": self.title,
            "description": self.description,
            "price": str(self.price),
            "quantity": self.quantity,
            "category": self.category,
            "condition": self.condition,
            "sku": self.sku,
            "brand": self.brand,
            "images": self.images,
            "shipping_weight": self.shipping_weight,
            "shipping_dimensions": self.shipping_dimensions,
            "ebay_id": self.ebay_id,
            "amazon_id": self.amazon_id,
            "tags": self.tags,
            "custom_fields": self.custom_fields,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Item":
        """Crea un Item da un dizionario."""
        # Converti il prezzo in Decimal
        if isinstance(data.get("price"), str):
            data["price"] = Decimal(data["price"])

        return cls(**data)
