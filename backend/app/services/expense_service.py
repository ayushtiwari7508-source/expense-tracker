"""Expense business logic."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundError
from backend.app.models.expense import Expense
from backend.app.schemas.common import SORTABLE_EXPENSE_FIELDS
from backend.app.schemas.expense import ExpenseCreate, ExpenseListParams, ExpenseUpdate


def _apply_filters(query: Select, params: ExpenseListParams) -> Select:
    """Apply list filters to a select statement."""
    if params.search:
        pattern = f"%{params.search.lower()}%"
        query = query.where(
            or_(
                func.lower(Expense.description).like(pattern),
                func.lower(Expense.category).like(pattern),
            )
        )
    if params.category is not None:
        query = query.where(Expense.category == params.category)
    if params.payment_method is not None:
        query = query.where(Expense.payment_method == params.payment_method)
    if params.date_from is not None:
        query = query.where(Expense.expense_date >= params.date_from)
    if params.date_to is not None:
        query = query.where(Expense.expense_date <= params.date_to)
    if params.min_amount is not None:
        query = query.where(Expense.amount >= params.min_amount)
    if params.max_amount is not None:
        query = query.where(Expense.amount <= params.max_amount)
    return query


def _apply_sorting(query: Select, params: ExpenseListParams) -> Select:
    """Apply whitelisted sorting to a select statement."""
    column = getattr(Expense, SORTABLE_EXPENSE_FIELDS[params.sort_by])
    order = column.desc() if params.sort_order == "desc" else column.asc()
    return query.order_by(order, Expense.id)


async def get_expense_owned(db: AsyncSession, user_id: UUID, expense_id: UUID) -> Expense:
    """Fetch an expense enforcing ownership; raises NotFoundError otherwise."""
    result = await db.execute(
        select(Expense).where(Expense.id == expense_id, Expense.user_id == user_id)
    )
    expense = result.scalar_one_or_none()
    if expense is None:
        raise NotFoundError("Expense not found")
    return expense


async def create_expense(db: AsyncSession, user_id: UUID, payload: ExpenseCreate) -> Expense:
    """Create a new expense for the user."""
    expense = Expense(
        user_id=user_id,
        amount=payload.amount,
        category=payload.category,
        description=payload.description,
        payment_method=payload.payment_method,
        expense_date=payload.expense_date,
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return expense


async def list_expenses(
    db: AsyncSession, user_id: UUID, params: ExpenseListParams
) -> tuple[list[Expense], int]:
    """Return a page of expenses plus the total matching count."""
    base = select(Expense).where(Expense.user_id == user_id)
    base = _apply_filters(base, params)

    count_query = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = _apply_sorting(base, params)
    query = query.offset((params.page - 1) * params.page_size).limit(params.page_size)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def update_expense(
    db: AsyncSession, user_id: UUID, expense_id: UUID, payload: ExpenseUpdate
) -> Expense:
    """Partially update an owned expense."""
    expense = await get_expense_owned(db, user_id, expense_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(expense, field, value)
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return expense


async def delete_expense(db: AsyncSession, user_id: UUID, expense_id: UUID) -> None:
    """Delete an owned expense."""
    expense = await get_expense_owned(db, user_id, expense_id)
    await db.delete(expense)
    await db.commit()


async def get_expenses_in_range(
    db: AsyncSession,
    user_id: UUID,
    start_date: date,
    end_date: date,
    category: str | None = None,
) -> list[Expense]:
    """Fetch all expenses for a user within an inclusive date range."""
    query = select(Expense).where(
        Expense.user_id == user_id,
        Expense.expense_date >= start_date,
        Expense.expense_date <= end_date,
    )
    if category is not None:
        query = query.where(Expense.category == category)
    result = await db.execute(query.order_by(Expense.expense_date))
    return list(result.scalars().all())


async def sum_expenses(
    db: AsyncSession,
    user_id: UUID,
    start_date: date,
    end_date: date,
    category: str | None = None,
) -> Decimal:
    """Sum expense amounts for a user within an inclusive range."""
    from sqlalchemy import case

    query = select(
        func.coalesce(
            func.sum(case((Expense.user_id == user_id, Expense.amount), else_=Decimal("0"))),
            Decimal("0"),
        )
    ).where(
        Expense.user_id == user_id,
        Expense.expense_date >= start_date,
        Expense.expense_date <= end_date,
    )
    if category is not None:
        query = query.where(Expense.category == category)
    result = await db.execute(query)
    return result.scalar_one()
