"""Helper per ConsignmentSale."""
from typing import List, Optional

from fastapi import Depends
from sqlalchemy import desc, extract
from sqlalchemy.orm import Session

from helpers import BaseHelper
from models.db import ConsignmentSale
from models.entities.consignment_sale import ConsignmentSaleUpdate
from utils.session import get_db


class ConsignmentSaleHelper(BaseHelper):

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get(self, sale_id: int) -> Optional[ConsignmentSale]:
        return self.db.query(ConsignmentSale).filter(ConsignmentSale.id == sale_id).first()

    def gets(
        self,
        year: Optional[int] = None,
        consignor: Optional[str] = None,
        paid_out: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[ConsignmentSale]:
        query = self.db.query(ConsignmentSale)
        if year is not None:
            query = query.filter(extract("year", ConsignmentSale.sale_date) == year)
        if consignor:
            query = query.filter(ConsignmentSale.consignor == consignor)
        if paid_out is not None:
            query = query.filter(ConsignmentSale.paid_out == paid_out)
        if search:
            like = f"%{search.lower()}%"
            query = query.filter(
                (ConsignmentSale.item.ilike(like))
                | (ConsignmentSale.consignor.ilike(like))
                | (ConsignmentSale.note.ilike(like))
                | (ConsignmentSale.buyer.ilike(like))
            )
        return query.order_by(desc(ConsignmentSale.sale_date), desc(ConsignmentSale.id)).all()

    def save(self, sale: ConsignmentSale) -> None:
        self.db.add(sale)
        self.db.commit()
        self.db.refresh(sale)

    def update(self, new_data: ConsignmentSaleUpdate, existing: ConsignmentSale) -> None:
        update_data = new_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing, key, value)
        self.db.commit()
        self.db.refresh(existing)

    def delete(self, sale: ConsignmentSale) -> None:
        self.db.delete(sale)
        self.db.commit()


def get_consignment_sale_helper(db: Session = Depends(get_db)) -> ConsignmentSaleHelper:
    return ConsignmentSaleHelper(db=db)
