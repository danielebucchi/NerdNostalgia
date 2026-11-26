"""
Un contenuto pubblicato su Instagram (post, Storia o Reel) con le sue
statistiche: la base per scegliere orari e hashtag (utils/instagram_stats.py).
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

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

    def __repr__(self):
        return f"<InstagramMedia({self.kind} {self.media_id}, reach={self.reach})>"
