import datetime
from datetime import datetime as dt

from fastapi import Depends

from helpers import BaseHelper
from sqlalchemy.orm import Session

from models.db import User
from models.entities.user import UserUpdate
from utils.session import get_db


class UserHelper(BaseHelper):

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get(self, field: str, value) -> User:
        if not hasattr(User, field):
            raise ValueError(f"Il campo '{field}' non esiste nel modello User")

        return self.db.query(User).filter(getattr(User, field) == value).first()

    def gets(self, is_active: bool, skip: int = 0, limit: int = 100):
        query = self.db.query(User)

        # Apply filters
        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        return query.offset(skip).limit(limit).all()

    def save(self, user: User):
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

    def update(self, new_user: UserUpdate, existing_user: User):
        update_data = new_user.dict(exclude_unset=True)

        for key, value in update_data.items():
            setattr(existing_user, key, value)

        existing_user.updated_at = dt.now(datetime.UTC)

        self.db.commit()
        self.db.refresh(existing_user)

    def delete(self, user: User):
        self.db.delete(user)
        self.db.commit()


def get_user_helper(db: Session = Depends(get_db)) -> UserHelper:
    return UserHelper(db=db)