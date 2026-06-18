"""
API endpoint Expense (spese generiche). Admin only.
"""
from collections import defaultdict
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from helpers.auth import require_admin
from helpers.expense import ExpenseHelper, get_expense_helper
from models.db import Expense, User
from models.entities.expense import (
    ExpenseCreate,
    ExpenseListResponse,
    ExpenseResponse,
    ExpenseUpdate,
)

router = APIRouter(prefix="/api/expenses", tags=["expenses"])


@router.get("/", response_model=ExpenseListResponse)
def list_expenses(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    category: Optional[str] = Query(None),
    related_to_cards: Optional[bool] = Query(None),
    related_to_creations: Optional[bool] = Query(None),
    paid_by: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    helper: ExpenseHelper = Depends(get_expense_helper),
    _admin: User = Depends(require_admin),
):
    items = helper.gets(
        year=year,
        category=category,
        related_to_cards=related_to_cards,
        related_to_creations=related_to_creations,
        paid_by=paid_by,
        search=search,
    )
    total = Decimal("0")
    total_card = Decimal("0")
    total_creation = Decimal("0")
    by_cat: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for e in items:
        amt = e.amount or Decimal("0")
        total += amt
        if e.related_to_cards:
            total_card += amt
        if e.related_to_creations:
            total_creation += amt
        cat_key = e.category or "—"
        by_cat[cat_key] += amt
    return ExpenseListResponse(
        items=[ExpenseResponse.model_validate(e) for e in items],
        total=len(items),
        total_amount=total,
        total_card_related=total_card,
        total_creation_related=total_creation,
        by_category=dict(by_cat),
    )


@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate,
    helper: ExpenseHelper = Depends(get_expense_helper),
    _admin: User = Depends(require_admin),
):
    exp = Expense(**payload.model_dump())
    exp.item = exp.item.strip()
    helper.save(exp)
    return ExpenseResponse.model_validate(exp)


@router.patch("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    helper: ExpenseHelper = Depends(get_expense_helper),
    _admin: User = Depends(require_admin),
):
    exp = helper.get(expense_id)
    if not exp:
        raise HTTPException(404, f"Spesa {expense_id} non trovata")
    helper.update(payload, exp)
    return ExpenseResponse.model_validate(exp)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int,
    helper: ExpenseHelper = Depends(get_expense_helper),
    _admin: User = Depends(require_admin),
):
    exp = helper.get(expense_id)
    if not exp:
        raise HTTPException(404, f"Spesa {expense_id} non trovata")
    helper.delete(exp)
    return None
