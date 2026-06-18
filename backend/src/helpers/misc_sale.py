"""
Helper per le vendite generiche.
"""
import datetime
from datetime import datetime as dt
from typing import List, Optional

from fastapi import Depends
from sqlalchemy import desc, nulls_last
from sqlalchemy.orm import Session

from helpers import BaseHelper
from models.db import MiscSale
from models.entities.misc_sale import MiscSaleUpdate
from utils.session import get_db


class MiscSaleHelper(BaseHelper):

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get(self, item_id: int) -> Optional[MiscSale]:
        return self.db.query(MiscSale).filter(MiscSale.id == item_id).first()

    def gets(
        self,
        year: Optional[int] = None,
        seller: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> List[MiscSale]:
        query = self.db.query(MiscSale)
        if year is not None:
            from sqlalchemy import extract
            query = query.filter(extract("year", MiscSale.sale_date) == year)
        if seller:
            query = query.filter(MiscSale.seller == seller)
        if kind:
            query = query.filter(MiscSale.kind == kind)
        return query.order_by(
            nulls_last(desc(MiscSale.sale_date)),
            desc(MiscSale.id),
        ).all()

    def save(self, item: MiscSale) -> None:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

    def update(self, new_data: MiscSaleUpdate, existing: MiscSale) -> None:
        update_data = new_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing, key, value)
        existing.updated_at = dt.now(datetime.UTC)
        self.db.commit()
        self.db.refresh(existing)

    def delete(self, item: MiscSale) -> None:
        self.db.delete(item)
        self.db.commit()


def get_misc_sale_helper(db: Session = Depends(get_db)) -> MiscSaleHelper:
    return MiscSaleHelper(db=db)
