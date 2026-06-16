"""
Modello Inquiry per SQLAlchemy.
"""
import enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as PgEnum
from sqlalchemy.orm import relationship

from .base import BaseModel


class InquiryStatus(enum.Enum):
    NEW = "NEW"
    READ = "READ"
    REPLIED = "REPLIED"
    CLOSED = "CLOSED"


class Inquiry(BaseModel):
    __tablename__ = "inquiries"

    article_id = Column(
        Integer,
        ForeignKey("articles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50))
    subject = Column(String(255))
    message = Column(Text, nullable=False)

    status = Column(
        PgEnum(InquiryStatus, name="inquiry_status", create_type=False),
        nullable=False,
        default=InquiryStatus.NEW,
        index=True,
    )

    ip_address = Column(String(45))
    admin_notes = Column(Text)
    replied_at = Column(DateTime)

    article = relationship("Article", backref="inquiries")

    def __repr__(self):
        return (
            f"<Inquiry(id={self.id}, email='{self.email}', "
            f"status='{self.status.value if self.status else None}')>"
        )
