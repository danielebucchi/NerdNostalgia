"""
Helper per la gestione dei markup di marketplace.
"""
import datetime
from datetime import datetime as dt
from typing import List, Optional

from fastapi import Depends
from sqlalchemy import asc, nulls_first
from sqlalchemy.orm import Session

from helpers import BaseHelper
from models.db import MarketplaceFee
from models.entities.marketplace_fee import MarketplaceFeeUpdate
from utils.session import get_db


class MarketplaceFeeHelper(BaseHelper):

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get(self, fee_id: int) -> Optional[MarketplaceFee]:
        return self.db.query(MarketplaceFee).filter(MarketplaceFee.id == fee_id).first()

    def gets(self, marketplace: Optional[str] = None) -> List[MarketplaceFee]:
        query = self.db.query(MarketplaceFee)
        if marketplace:
            query = query.filter(MarketplaceFee.marketplace == marketplace)
        return query.order_by(
            asc(MarketplaceFee.marketplace),
            nulls_first(asc(MarketplaceFee.category_id)),
            asc(MarketplaceFee.markup_percent),
        ).all()

    def save(self, fee: MarketplaceFee) -> None:
        self.db.add(fee)
        self.db.commit()
        self.db.refresh(fee)

    def update(self, new_data: MarketplaceFeeUpdate, existing: MarketplaceFee) -> None:
        update_data = new_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing, key, value)
        existing.updated_at = dt.now(datetime.UTC)
        self.db.commit()
        self.db.refresh(existing)

    def delete(self, fee: MarketplaceFee) -> None:
        self.db.delete(fee)
        self.db.commit()


def get_marketplace_fee_helper(db: Session = Depends(get_db)) -> MarketplaceFeeHelper:
    return MarketplaceFeeHelper(db=db)
