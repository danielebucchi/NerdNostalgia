"""
Iscritti alla newsletter senza account.

Chi ha un account dà il consenso dalla spunta (users.marketing_consent);
qui finisce chi lascia solo l'email dal riquadro nel footer. Il consenso
vale solo dopo la conferma dal link nell'email (doppio opt-in):
confirmed_at pieno e revoked_at vuoto = riceve la newsletter.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from .base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    confirm_token = Column(String(64), index=True)
    confirm_sent_at = Column(DateTime)
    confirmed_at = Column(DateTime)
    revoked_at = Column(DateTime)
    unsubscribe_token = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=_utc_now, nullable=False)

    @property
    def attivo(self) -> bool:
        return self.confirmed_at is not None and self.revoked_at is None

    def __repr__(self):
        return f"<NewsletterSubscriber(email='{self.email}', attivo={self.attivo})>"
