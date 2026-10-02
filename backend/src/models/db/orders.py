"""
Modelli Order + OrderItem per SQLAlchemy.

Pagamento out-of-band (paypal.me): l'ordine parte come PENDING quando
il compratore compila il form e diventa PAID solo via conferma admin.
"""
import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import Enum as PgEnum
from sqlalchemy.orm import relationship

from .base import BaseModel


class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    # Pratica chiusa: pacco consegnato e nulla in sospeso. Si arriva qui
    # solo da SHIPPED.
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Order(BaseModel):
    __tablename__ = "orders"

    # Buyer
    buyer_name = Column(String(255), nullable=False)
    buyer_email = Column(String(255), nullable=False, index=True)
    buyer_phone = Column(String(50))

    # Shipping address
    ship_street = Column(String(255), nullable=False)
    ship_city = Column(String(120), nullable=False)
    ship_postal_code = Column(String(20), nullable=False)
    ship_province = Column(String(120))
    ship_country = Column(String(80), nullable=False, default="Italia")

    # Pricing (snapshot al checkout)
    subtotal = Column(Numeric(10, 2), nullable=False)
    shipping_total = Column(Numeric(10, 2), nullable=False)
    grand_total = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="EUR")

    notes = Column(Text)
    # Scambio a mano: offerta ritirata dal sito. Resta per gli ordini storici
    # (l'admin mostra ancora il badge); i nuovi ordini sono sempre False.
    hand_exchange = Column(Boolean, nullable=False, default=False)
    status = Column(
        PgEnum(OrderStatus, name="order_status", create_type=False),
        nullable=False,
        default=OrderStatus.PENDING,
        index=True,
    )
    paid_at = Column(DateTime)
    shipped_at = Column(DateTime)
    completed_at = Column(DateTime)
    cancelled_at = Column(DateTime)

    # Spedizione: il codice e' obbligatorio per passare a SPEDITO, cosi' non
    # si perde traccia di un pacco gia' partito.
    tracking_carrier = Column(String(80))
    tracking_code = Column(String(120))
    # Link diretto alla pagina del corriere: evita al compratore di cercare
    # il sito giusto e incollarci dentro il codice.
    tracking_url = Column(String(500))
    admin_notes = Column(Text)

    ip_address = Column(String(45))

    # Stripe Checkout
    stripe_session_id = Column(String(120))
    stripe_payment_intent = Column(String(120))

    # Token opaco generato alla creazione: con (id + token) il compratore puo'
    # leggere lo stato del proprio ordine senza autenticarsi, e il carrello
    # sa quando svuotarsi. Non va mai mostrato nelle liste pubbliche.
    public_token = Column(String(64))

    # PayPal Orders v2 (bottoni ufficiali)
    paypal_order_id = Column(String(64))
    paypal_capture_id = Column(String(64))

    # Profilo del cliente. NULL per gli acquisti da ospite: si compra anche
    # senza account, e l'ordine si riaggancia se poi ci si registra con la
    # stessa email.
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Locker InPost: id del punto (es. "IT12345") e descrizione leggibile.
    # I campi ship_* contengono l'indirizzo del locker, che e' la vera
    # destinazione della spedizione.
    inpost_point_id = Column(String(64))
    inpost_point_name = Column(String(255))

    # Assicurazione: scelta del compratore + quanto gli e' costata. La cifra
    # la salviamo perche' le tariffe cambiano e l'ordine deve restare
    # leggibile fra un anno.
    insured = Column(Boolean, nullable=False, default=False)
    insurance_fee = Column(Numeric(10, 2), nullable=False, default=0)

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class OrderItem(BaseModel):
    __tablename__ = "order_items"

    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id = Column(
        Integer,
        ForeignKey("articles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title_snapshot = Column(String(255), nullable=False)
    price_snapshot = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)

    order = relationship("Order", back_populates="items")
    article = relationship("Article", foreign_keys=[article_id])
