"""
Rubrica degli indirizzi di spedizione del cliente.

Gli ordini non puntano qui: tengono la loro copia dei campi ship_*. Un
indirizzo cancellato o corretto dopo un trasloco non deve riscrivere la
storia di dove i pacchi sono andati davvero.
"""
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class ShippingAddress(BaseModel):
    __tablename__ = "shipping_addresses"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Come lo chiama il cliente ("Casa", "Ufficio"): facoltativo.
    label = Column(String(60))

    # Il destinatario puo' non essere l'intestatario dell'account: si
    # spedisce anche a un regalo o a un parente.
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50))

    street = Column(String(255), nullable=False)
    city = Column(String(120), nullable=False)
    postal_code = Column(String(20), nullable=False)
    province = Column(String(120))
    country = Column(String(80), nullable=False, default="Italia")

    # Ne resta acceso uno solo per utente: ci pensa l'applicazione.
    is_default = Column(Boolean, nullable=False, default=False)

    user = relationship("User")

    def __repr__(self):
        return f"<ShippingAddress(user={self.user_id}, {self.street}, {self.city})>"
