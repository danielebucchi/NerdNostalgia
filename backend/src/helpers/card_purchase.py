"""
Helper per le spese carte all'ingrosso.
"""
import datetime
from datetime import datetime as dt
from typing import List, Optional

from fastapi import Depends
from sqlalchemy import desc, nulls_last
from sqlalchemy.orm import Session

from helpers import BaseHelper
from models.db import CardPurchase
from models.entities.card_purchase import CardPurchaseUpdate
from utils.session import get_db


class CardPurchaseHelper(BaseHelper):

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get(self, item_id: int) -> Optional[CardPurchase]:
        return self.db.query(CardPurchase).filter(CardPurchase.id == item_id).first()

    def gets(self, year: Optional[int] = None) -> List[CardPurchase]:
        query = self.db.query(CardPurchase)
        if year is not None:
            from sqlalchemy import extract
            query = query.filter(extract("year", CardPurchase.purchase_date) == year)
        return query.order_by(
            nulls_last(desc(CardPurchase.purchase_date)),
            desc(CardPurchase.id),
        ).all()

    def save(self, item: CardPurchase) -> None:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

    def update(self, new_data: CardPurchaseUpdate, existing: CardPurchase) -> None:
        update_data = new_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing, key, value)
        existing.updated_at = dt.now(datetime.UTC)
        self.db.commit()
        self.db.refresh(existing)

    def delete(self, item: CardPurchase) -> None:
        self.db.delete(item)
        self.db.commit()


def get_card_purchase_helper(db: Session = Depends(get_db)) -> CardPurchaseHelper:
    return CardPurchaseHelper(db=db)
