"""
Scanner carte: la coda degli scan da confermare e l'indice locale dei
blueprint CardTrader.

Lo scan non diventa subito una carta della collezione: il riconoscimento
propone, una persona conferma. Una carta sbagliata in catalogo la si
scopre quando qualcuno l'ha comprata — e a quel punto e' tardi.

L'indice serve perche' CardTrader non ha una ricerca "dammi le carte col
numero 25 di tutte le espansioni Pokemon": ha solo l'export per singola
espansione. Per i set che non stampano la sigla (Pokemon fino a Sole e
Luna) il numero e' l'unico appiglio, e va cercato ovunque.
"""
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)

from .base import Base, BaseModel, _utc_now


class CardScanStatus:
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    DISCARDED = "DISCARDED"


class CardScan(BaseModel):
    __tablename__ = "card_scans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','CONFIRMED','DISCARDED')",
            name="card_scans_status_check",
        ),
    )

    image_url = Column(String(500), nullable=False)
    original_filename = Column(String(255))
    game_id = Column(Integer)
    # Espansione fissata da chi scansiona (una scatola = un set, di solito)
    expansion_id = Column(Integer)
    status = Column(String(20), nullable=False, default=CardScanStatus.PENDING, index=True)
    # LetturaCarta.as_dict(): numero, sigla, lingua, testo letto
    ocr = Column(JSON, nullable=False, default=dict)
    # Candidati ordinati: [{blueprint_id, name, expansion_name, number, image_url, score, ...}]
    candidates = Column(JSON, nullable=False, default=list)
    confidence = Column(String(10))  # alta / media / bassa
    # Retro della carta (facoltativo): lo sbiancamento dei bordi si vede
    # soprattutto li'.
    back_image_url = Column(String(500))
    # Analisi della carta scelta: reverse, prima edizione, condizione
    features = Column(JSON, nullable=False, default=dict)
    error = Column(Text)
    personal_card_id = Column(Integer, ForeignKey("personal_cards.id", ondelete="SET NULL"))


class CardBlueprint(Base):
    """Una carta singola del catalogo CardTrader (niente buste e box)."""
    __tablename__ = "card_blueprints"

    id = Column(BigInteger, primary_key=True)  # = blueprint_id CardTrader
    game_id = Column(Integer, nullable=False, index=True)
    expansion_id = Column(Integer, nullable=False, index=True)
    expansion_code = Column(String(30), index=True)
    expansion_name = Column(String(200))
    name = Column(String(255), nullable=False)
    version = Column(String(255))
    collector_number = Column(String(50))
    # _norm_number(collector_number): "025" → "25", "OP01-064" → "op01064"
    number_norm = Column(String(50), index=True)
    image_url = Column(String(500))
    # dHash dell'immagine CardTrader, calcolato la prima volta che serve
    dhash = Column(String(64))
    # Attributi che CardTrader ammette per questa carta, separati da
    # virgola ("first_edition,pokemon_reverse"): dicono se ha senso cercare
    # la prima edizione o il reverse sullo scan.
    editable = Column(String(255))
    indexed_at = Column(DateTime, nullable=False, default=_utc_now)
