"""
Helper per Lot.
"""
from typing import List, Optional

from fastapi import Depends
from sqlalchemy import desc, nulls_last
from sqlalchemy.orm import Session

from helpers import BaseHelper
from models.db import Lot, LotStatus
from models.entities.lot import LotUpdate
from utils.session import get_db


class LotHelper(BaseHelper):

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get(self, lot_id: int) -> Optional[Lot]:
        return self.db.query(Lot).filter(Lot.id == lot_id).first()

    def get_by_code(self, code: str) -> Optional[Lot]:
        return self.db.query(Lot).filter(Lot.code == code).first()

    def gets(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Lot]:
        query = self.db.query(Lot)
        if status:
            query = query.filter(Lot.status == status)
        if search:
            like = f"%{search.lower()}%"
            query = query.filter(
                (Lot.code.ilike(like)) | (Lot.title.ilike(like))
            )
        return query.order_by(
            nulls_last(desc(Lot.purchase_date)),
            desc(Lot.id),
        ).all()

    def next_code(self) -> str:
        """Genera prossimo codice sequenziale L0001, L0002, ...
        Portable PG/SQLite: filtra LIKE 'L%', poi calcola in Python il max
        della parte numerica. Volumi attesi: decine/centinaia → trascurabile."""
        rows = self.db.query(Lot.code).filter(Lot.code.like("L%")).all()
        max_seq = 0
        for (code,) in rows:
            if code and len(code) > 1 and code[1:].isdigit():
                seq = int(code[1:])
                if seq > max_seq:
                    max_seq = seq
        return f"L{max_seq + 1:04d}"

    def save(self, lot: Lot) -> None:
        if not lot.code:
            lot.code = self.next_code()
        if not lot.status:
            lot.status = LotStatus.OPEN
        self.db.add(lot)
        self.db.commit()
        self.db.refresh(lot)

    def update(self, new_data: LotUpdate, existing: Lot) -> None:
        update_data = new_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing, key, value)
        self.db.commit()
        self.db.refresh(existing)

    def delete(self, lot: Lot) -> None:
        self.db.delete(lot)
        self.db.commit()


def get_lot_helper(db: Session = Depends(get_db)) -> LotHelper:
    return LotHelper(db=db)
