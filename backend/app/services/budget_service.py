"""Budget business logic."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.models.budget import Budget
from backend.app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetUtilization
from backend.app.services.expense_service import get_expenses_in_range, sum_expenses


def _status_for(utilization: float, threshold: Decimal) -> str:
    """Derive budget status from utilization and the budget's threshold."""
    if utilization >= 100:
        return "EXCEEDED"
    if utilization >= float(threshold):
        return "WARNING"
    return "NORMAL"


def compute_utilization(
    budget: Budget, amount_spent: Decimal
) -> BudgetUtilization:
    """Compute derived utilization metrics (never persisted)."""
    budget_amount = budget.amount
    remaining = budget_amount - amount_spent
    utilization_pct = (
        float(amount_spent / budget_amount * 100) if budget_amount > 0 else 0.0
    )
    return BudgetUtilization(
        budget_amount=budget_amount,
        amount_spent=amount_spent,
        remaining_amount=remaining,
        utilization_percentage=round(utilization_pct, 2),
        status=_status_for(utilization_pct, budget.alert_threshold),
    )


async def spent_for_budget(
    db: AsyncSession, user_id: UUID, budget: Budget
) -> Decimal:
    """Sum the user's expenses relevant to a budget (category scoped or overall)."""
    return await sum_expenses(
        db,
        user_id,
        budget.start_date,
        budget.end_date,
        category=budget.category,
    )


async def get_budget_owned(db: AsyncSession, user_id: UUID, budget_id: UUID) -> Budget:
    """Fetch a budget enforcing ownership."""
    result = await db.execute(
        select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
    )
    budget = result.scalar_one_or_none()
    if budget is None:
        raise NotFoundError("Budget not found")
    return budget


async def create_budget(db: AsyncSession, user_id: UUID, payload: BudgetCreate) -> Budget:
    """Create a new budget."""
    budget = Budget(
        user_id=user_id,
        category=payload.category,
        amount=payload.amount,
        start_date=payload.start_date,
        end_date=payload.end_date,
        alert_threshold=payload.alert_threshold,
    )
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return budget


async def list_budgets(db: AsyncSession, user_id: UUID) -> list[Budget]:
    """List all budgets for a user, newest first."""
    result = await db.execute(
        select(Budget)
        .where(Budget.user_id == user_id)
        .order_by(Budget.start_date.desc(), Budget.created_at.desc())
    )
    return list(result.scalars().all())


async def update_budget(
    db: AsyncSession, user_id: UUID, budget_id: UUID, payload: BudgetUpdate
) -> Budget:
    """Partially update an owned budget, validating the resulting date range."""
    budget = await get_budget_owned(db, user_id, budget_id)
    data = payload.model_dump(exclude_unset=True)
    start = data.get("start_date", budget.start_date)
    end = data.get("end_date", budget.end_date)
    if isinstance(start, date) and isinstance(end, date) and start > end:
        raise ValidationError("start_date must be on or before end_date")

    for field, value in data.items():
        setattr(budget, field, value)
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return budget


async def delete_budget(db: AsyncSession, user_id: UUID, budget_id: UUID) -> None:
    """Delete an owned budget."""
    budget = await get_budget_owned(db, user_id, budget_id)
    await db.delete(budget)
    await db.commit()
