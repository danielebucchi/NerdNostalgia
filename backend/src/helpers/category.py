"""
Helper per la gestione delle categorie (categoria/sottocategoria).
"""
import datetime
from datetime import datetime as dt
from typing import List, Optional

from fastapi import Depends
from sqlalchemy import asc, nulls_first
from sqlalchemy.orm import Session

from helpers import BaseHelper
from models.db import Category
from models.entities.category import CategoryUpdate
from utils.session import get_db


class CategoryHelper(BaseHelper):

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get(self, category_id: int) -> Optional[Category]:
        return self.db.query(Category).filter(Category.id == category_id).first()

    def get_by_slug(self, slug: str) -> Optional[Category]:
        return self.db.query(Category).filter(Category.slug == slug).first()

    def gets(self) -> List[Category]:
        return (
            self.db.query(Category)
            .order_by(
                nulls_first(asc(Category.parent_id)),
                asc(Category.display_order),
                asc(Category.name),
            )
            .all()
        )

    def get_descendant_ids(self, root_id: int) -> List[int]:
        """Ritorna gli id della categoria + tutti i suoi discendenti."""
        all_cats = self.gets()
        children_by_parent: dict[Optional[int], List[Category]] = {}
        for c in all_cats:
            children_by_parent.setdefault(c.parent_id, []).append(c)

        result: List[int] = []
        stack = [root_id]
        while stack:
            current = stack.pop()
            result.append(current)
            for child in children_by_parent.get(current, []):
                stack.append(child.id)
        return result

    def save(self, category: Category) -> None:
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)

    def update(self, new_data: CategoryUpdate, existing: Category) -> None:
        update_data = new_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing, key, value)
        existing.updated_at = dt.now(datetime.UTC)
        self.db.commit()
        self.db.refresh(existing)

    def delete(self, category: Category) -> None:
        self.db.delete(category)
        self.db.commit()


def get_category_helper(db: Session = Depends(get_db)) -> CategoryHelper:
    return CategoryHelper(db=db)
