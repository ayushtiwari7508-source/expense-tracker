"""Expense CRUD routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from backend.app.api.deps import CurrentUser, DbSession
from backend.app.schemas.expense import (
    ExpenseCreate,
    ExpenseListParams,
    ExpenseResponse,
    ExpenseUpdate,
)
from backend.app.services import expense_service

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an expense",
)
async def create_expense(payload: ExpenseCreate, current_user: CurrentUser, db: DbSession):
    expense = await expense_service.create_expense(db, current_user.id, payload)
    return ExpenseResponse.model_validate(expense)


@router.get(
    "",
    response_model=dict,
    summary="List expenses",
    description=(
        "Paginated, filterable, sortable list of the authenticated user's "
        "expenses. Sorting is restricted to a whitelist of fields."
    ),
)
async def list_expenses(
    current_user: CurrentUser,
    db: DbSession,
    params: Annotated[ExpenseListParams, Query()],
) -> dict:
    items, total = await expense_service.list_expenses(db, current_user.id, params)
    return {
        "items": [ExpenseResponse.model_validate(e) for e in items],
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "pages": (total + params.page_size - 1) // params.page_size,
    }


@router.get(
    "/{expense_id}",
    response_model=ExpenseResponse,
    summary="Get an expense by ID",
    responses={404: {"description": "Expense not found"}},
)
async def get_expense(expense_id: UUID, current_user: CurrentUser, db: DbSession):
    expense = await expense_service.get_expense_owned(db, current_user.id, expense_id)
    return ExpenseResponse.model_validate(expense)


@router.patch(
    "/{expense_id}",
    response_model=ExpenseResponse,
    summary="Update an expense",
)
async def update_expense(
    expense_id: UUID, payload: ExpenseUpdate, current_user: CurrentUser, db: DbSession
):
    expense = await expense_service.update_expense(
        db, current_user.id, expense_id, payload
    )
    return ExpenseResponse.model_validate(expense)


@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an expense",
)
async def delete_expense(expense_id: UUID, current_user: CurrentUser, db: DbSession) -> None:
    await expense_service.delete_expense(db, current_user.id, expense_id)
