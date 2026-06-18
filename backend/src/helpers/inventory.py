"""
Helper per inventory_items.
"""
import datetime
from datetime import datetime as dt
from typing import List, Optional

from fastapi import Depends
from sqlalchemy import desc, extract, nulls_last
from sqlalchemy.orm import Session

from helpers import BaseHelper
from models.db import InventoryItem, Lot
from models.entities.inventory import InventoryItemUpdate
from utils.session import get_db


class InventoryHelper(BaseHelper):

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get(self, item_id: int) -> Optional[InventoryItem]:
        return (
            self.db.query(InventoryItem)
            .filter(InventoryItem.id == item_id)
            .first()
        )

    def gets(
        self,
        lot_id: Optional[int] = None,
        year: Optional[int] = None,
        category_id: Optional[int] = None,
        sold_only: Optional[bool] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[InventoryItem]:
        query = self.db.query(InventoryItem).join(Lot, InventoryItem.lot_id == Lot.id)
        if lot_id is not None:
            query = query.filter(InventoryItem.lot_id == lot_id)
        if year is not None:
            query = query.filter(
                (extract("year", Lot.purchase_date) == year)
                | (extract("year", InventoryItem.sold_date) == year)
            )
        if category_id is not None:
            query = query.filter(InventoryItem.category_id == category_id)
        if status:
            query = query.filter(InventoryItem.status == status)
        if sold_only is True:
            query = query.filter(InventoryItem.sold_date.isnot(None))
        elif sold_only is False:
            query = query.filter(InventoryItem.sold_date.is_(None))
        if search:
            like = f"%{search.lower()}%"
            query = query.filter(
                InventoryItem.title.ilike(like)
                | InventoryItem.notes.ilike(like)
                | InventoryItem.card_collection.ilike(like)
                | InventoryItem.card_number.ilike(like)
                | Lot.code.ilike(like)
                | Lot.title.ilike(like)
            )
        query = query.order_by(
            nulls_last(desc(Lot.purchase_date)),
            desc(InventoryItem.id),
        )
        if limit:
            query = query.limit(limit)
        return query.all()

    def save(self, item: InventoryItem) -> None:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

    def update(self, new_data: InventoryItemUpdate, existing: InventoryItem) -> None:
        update_data = new_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing, key, value)
        existing.updated_at = dt.now(datetime.UTC)
        self.db.commit()
        self.db.refresh(existing)

    def delete(self, item: InventoryItem) -> None:
        self.db.delete(item)
        self.db.commit()


def get_inventory_helper(db: Session = Depends(get_db)) -> InventoryHelper:
    return InventoryHelper(db=db)
