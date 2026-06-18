"""
Helper per Expense.
"""
from typing import List, Optional

from fastapi import Depends
from sqlalchemy import desc, extract
from sqlalchemy.orm import Session

from helpers import BaseHelper
from models.db import Expense
from models.entities.expense import ExpenseUpdate
from utils.session import get_db


class ExpenseHelper(BaseHelper):

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get(self, expense_id: int) -> Optional[Expense]:
        return self.db.query(Expense).filter(Expense.id == expense_id).first()

    def gets(
        self,
        year: Optional[int] = None,
        category: Optional[str] = None,
        related_to_cards: Optional[bool] = None,
        related_to_creations: Optional[bool] = None,
        paid_by: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Expense]:
        query = self.db.query(Expense)
        if year is not None:
            query = query.filter(extract("year", Expense.spend_date) == year)
        if category:
            query = query.filter(Expense.category == category)
        if related_to_cards is not None:
            query = query.filter(Expense.related_to_cards == related_to_cards)
        if related_to_creations is not None:
            query = query.filter(Expense.related_to_creations == related_to_creations)
        if paid_by:
            query = query.filter(Expense.paid_by == paid_by)
        if search:
            like = f"%{search.lower()}%"
            query = query.filter(
                (Expense.item.ilike(like))
                | (Expense.note.ilike(like))
                | (Expense.category.ilike(like))
            )
        return query.order_by(desc(Expense.spend_date), desc(Expense.id)).all()

    def save(self, expense: Expense) -> None:
        self.db.add(expense)
        self.db.commit()
        self.db.refresh(expense)

    def update(self, new_data: ExpenseUpdate, existing: Expense) -> None:
        update_data = new_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing, key, value)
        self.db.commit()
        self.db.refresh(existing)

    def delete(self, expense: Expense) -> None:
        self.db.delete(expense)
        self.db.commit()


def get_expense_helper(db: Session = Depends(get_db)) -> ExpenseHelper:
    return ExpenseHelper(db=db)
