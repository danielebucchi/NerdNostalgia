"""Helper per Platform."""
from typing import List, Optional

from fastapi import Depends
from sqlalchemy import asc
from sqlalchemy.orm import Session

from helpers import BaseHelper
from models.db import Platform
from models.entities.platform import PlatformUpdate, _slugify
from utils.session import get_db


class PlatformHelper(BaseHelper):

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get(self, platform_id: int) -> Optional[Platform]:
        return self.db.query(Platform).filter(Platform.id == platform_id).first()

    def get_by_slug(self, slug: str) -> Optional[Platform]:
        return self.db.query(Platform).filter(Platform.slug == slug).first()

    def gets(self, active_only: bool = False) -> List[Platform]:
        query = self.db.query(Platform)
        if active_only:
            query = query.filter(Platform.is_active.is_(True))
        return query.order_by(asc(Platform.display_order), asc(Platform.name)).all()

    def save(self, platform: Platform) -> None:
        if not platform.slug:
            platform.slug = _slugify(platform.name)
        self.db.add(platform)
        self.db.commit()
        self.db.refresh(platform)

    def update(self, new_data: PlatformUpdate, existing: Platform) -> None:
        update_data = new_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing, key, value)
        self.db.commit()
        self.db.refresh(existing)

    def delete(self, platform: Platform) -> None:
        self.db.delete(platform)
        self.db.commit()


def get_platform_helper(db: Session = Depends(get_db)) -> PlatformHelper:
    return PlatformHelper(db=db)
