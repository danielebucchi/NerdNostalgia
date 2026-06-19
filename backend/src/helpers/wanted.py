"""
Helper per la gestione degli articoli cerco/compro.
"""
import datetime
from datetime import datetime as dt
from decimal import Decimal
from typing import List, Optional, Tuple

from fastapi import Depends
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from helpers import BaseHelper
from models.db import ArticleCondition, WantedItem, WantedStatus
from models.entities.wanted import WantedItemUpdate
from utils.session import get_db


def _status_value(status) -> str:
    if status is None:
        return ""
    return status.value if hasattr(status, "value") else str(status)


class WantedItemHelper(BaseHelper):

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get(self, field: str, value) -> Optional[WantedItem]:
        if not hasattr(WantedItem, field):
            raise ValueError(f"Il campo '{field}' non esiste nel modello WantedItem")
        return self.db.query(WantedItem).filter(getattr(WantedItem, field) == value).first()

    def gets(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[WantedStatus] = None,
        category_ids: Optional[List[int]] = None,
        condition: Optional[ArticleCondition] = None,
        max_budget: Optional[Decimal] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[WantedItem], int]:
        query = self.db.query(WantedItem)

        if status is not None:
            query = query.filter(WantedItem.status == status)
        if category_ids:
            query = query.filter(WantedItem.category_id.in_(category_ids))
        if condition is not None:
            query = query.filter(WantedItem.preferred_condition == condition)
        if max_budget is not None:
            query = query.filter(
                (WantedItem.max_price == None) | (WantedItem.max_price <= max_budget)  # noqa: E711
            )
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                WantedItem.title.ilike(pattern)
                | WantedItem.description.ilike(pattern)
            )

        total = query.count()
        items = (
            query.order_by(desc(WantedItem.priority), desc(WantedItem.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    def save(self, item: WantedItem) -> None:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

    def update(self, new_data: WantedItemUpdate, existing: WantedItem) -> None:
        update_data = new_data.model_dump(exclude_unset=True)
        previous_status_val = _status_value(existing.status)

        for key, value in update_data.items():
            setattr(existing, key, value)

        new_status_val = _status_value(existing.status)
        if "status" in update_data and new_status_val != previous_status_val:
            if new_status_val == WantedStatus.FULFILLED.value and not existing.fulfilled_at:
                existing.fulfilled_at = dt.now(datetime.UTC)

        existing.updated_at = dt.now(datetime.UTC)
        self.db.commit()
        self.db.refresh(existing)

    def delete(self, item: WantedItem) -> None:
        self.db.delete(item)
        self.db.commit()

    def reorder(self, ordered_ids: List[int]) -> None:
        """Imposta priority decrescente (n-1, n-2, ..., 0) in base alla
        posizione nella lista."""
        n = len(ordered_ids)
        for position, wanted_id in enumerate(ordered_ids):
            item = self.get("id", wanted_id)
            if item is not None:
                item.priority = max(0, n - 1 - position)
        self.db.commit()


def get_wanted_helper(db: Session = Depends(get_db)) -> WantedItemHelper:
    return WantedItemHelper(db=db)
