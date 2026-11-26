"""
Un contenuto pubblicato su Instagram (post, Storia o Reel) con le sue
statistiche: la base per scegliere orari e hashtag (utils/instagram_stats.py).
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text

from .base import Base


class InstagramMedia(Base):
    __tablename__ = "instagram_media"

    media_id = Column(String(40), primary_key=True)
    kind = Column(String(10), nullable=False)          # post, story, reel
    published_at = Column(DateTime, nullable=False)    # ora italiana
    slot = Column(String(5))                           # "18:30": l'orario scelto, se l'abbiamo scelto noi
    n_items = Column(Integer, nullable=False, default=1)
    fallback = Column(Boolean, nullable=False, default=False)
    hashtags = Column(Text, nullable=False, default="")
    reach = Column(Integer)
    views = Column(Integer)
    saved = Column(Integer)
    shares = Column(Integer)
    interactions = Column(Integer)
    insights_at = Column(DateTime)
    article_ids = Column(Text, nullable=False, default="")  # "12 34 56": per i link in DM
    rubrica = Column(String(20))                             # la rubrica del giorno, se lo e'

    def __repr__(self):
        return f"<InstagramMedia({self.kind} {self.media_id}, reach={self.reach})>"


class InstagramReply(Base):
    """Un commento a cui il bot ha gia' risposto in privato."""
    __tablename__ = "instagram_replies"

    comment_id = Column(String(40), primary_key=True)
    media_id = Column(String(40), nullable=False)
    replied_at = Column(DateTime, nullable=False)


class CardPriceHistory(Base):
    """Il valore di mercato di una carta a ogni rivalutazione."""
    __tablename__ = "card_price_history"

    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey("personal_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    value = Column(Numeric(10, 2), nullable=False)
    recorded_at = Column(DateTime, nullable=False)
