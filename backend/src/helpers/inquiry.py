"""
Helper per la gestione delle richieste di contatto.
"""
import datetime
from datetime import datetime as dt
from typing import List, Optional, Tuple

from fastapi import Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from helpers import BaseHelper
from models.db import Inquiry, InquiryStatus
from models.entities.inquiry import InquiryUpdate
from utils.session import get_db


def _status_value(status) -> str:
    """Estrae il valore string da un enum o stringa."""
    if status is None:
        return ""
    return status.value if hasattr(status, "value") else str(status)


class InquiryHelper(BaseHelper):

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get(self, field: str, value) -> Optional[Inquiry]:
        if not hasattr(Inquiry, field):
            raise ValueError(f"Il campo '{field}' non esiste nel modello Inquiry")
        return self.db.query(Inquiry).filter(getattr(Inquiry, field) == value).first()

    def gets(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[InquiryStatus] = None,
        article_id: Optional[int] = None,
        email: Optional[str] = None,
    ) -> Tuple[List[Inquiry], int]:
        query = self.db.query(Inquiry)

        if status is not None:
            query = query.filter(Inquiry.status == status)
        if article_id is not None:
            query = query.filter(Inquiry.article_id == article_id)
        if email:
            query = query.filter(Inquiry.email == email)

        total = query.count()
        items = (
            query.order_by(desc(Inquiry.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    def save(self, inquiry: Inquiry) -> None:
        self.db.add(inquiry)
        self.db.commit()
        self.db.refresh(inquiry)

    def update(self, new_data: InquiryUpdate, existing: Inquiry) -> None:
        update_data = new_data.model_dump(exclude_unset=True)
        previous_status_val = _status_value(existing.status)

        for key, value in update_data.items():
            setattr(existing, key, value)

        new_status_val = _status_value(existing.status)
        if "status" in update_data and new_status_val != previous_status_val:
            if new_status_val == InquiryStatus.REPLIED.value and not existing.replied_at:
                existing.replied_at = dt.now(datetime.UTC)

        existing.updated_at = dt.now(datetime.UTC)
        self.db.commit()
        self.db.refresh(existing)

    def delete(self, inquiry: Inquiry) -> None:
        self.db.delete(inquiry)
        self.db.commit()


def get_inquiry_helper(db: Session = Depends(get_db)) -> InquiryHelper:
    return InquiryHelper(db=db)
