"""
Helper per PersonalCard.
"""
from typing import List, Optional

from fastapi import Depends
from sqlalchemy import desc, nulls_last
from sqlalchemy.orm import Session

from helpers import BaseHelper
from models.db import PersonalCard
from models.entities.personal_card import PersonalCardUpdate
from utils.session import get_db


class PersonalCardHelper(BaseHelper):

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get(self, card_id: int) -> Optional[PersonalCard]:
        return self.db.query(PersonalCard).filter(PersonalCard.id == card_id).first()

    def gets(
        self,
        owned_by: Optional[str] = None,
        collection: Optional[str] = None,
        bulk_source: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[PersonalCard]:
        query = self.db.query(PersonalCard)
        if owned_by:
            query = query.filter(PersonalCard.owned_by == owned_by)
        if collection:
            query = query.filter(PersonalCard.collection.ilike(f"%{collection}%"))
        if bulk_source:
            query = query.filter(PersonalCard.bulk_source == bulk_source)
        if status:
            query = query.filter(PersonalCard.status == status)
        if search:
            like = f"%{search.lower()}%"
            query = query.filter(
                (PersonalCard.name.ilike(like))
                | (PersonalCard.collection.ilike(like))
                | (PersonalCard.card_number.ilike(like))
                | (PersonalCard.bulk_source.ilike(like))
                | (PersonalCard.notes.ilike(like))
            )
        return query.order_by(
            nulls_last(desc(PersonalCard.sold_date)),
            nulls_last(desc(PersonalCard.purchase_date)),
            desc(PersonalCard.id),
        ).all()

    def save(self, card: PersonalCard) -> None:
        self.db.add(card)
        self.db.commit()
        self.db.refresh(card)

    def update(self, new_data: PersonalCardUpdate, existing: PersonalCard) -> None:
        update_data = new_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing, key, value)
        self.db.commit()
        self.db.refresh(existing)

    def delete(self, card: PersonalCard) -> None:
        self.db.delete(card)
        self.db.commit()


def get_personal_card_helper(db: Session = Depends(get_db)) -> PersonalCardHelper:
    return PersonalCardHelper(db=db)
