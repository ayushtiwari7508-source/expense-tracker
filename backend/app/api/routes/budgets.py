"""Budget routes with computed utilization."""

from uuid import UUID

from fastapi import APIRouter, status

from backend.app.api.deps import CurrentUser, DbSession
from backend.app.schemas.budget import (
    BudgetCreate,
    BudgetResponse,
    BudgetUpdate,
    BudgetWithUtilization,
)
from backend.app.services import alert_service, budget_service

router = APIRouter(prefix="/budgets", tags=["Budgets"])


async def _budget_with_utilization(db, user_id, budget) -> BudgetWithUtilization:
    """Serialize a budget together with its live utilization and alerts."""
    spent = await budget_service.spent_for_budget(db, user_id, budget)
    utilization = budget_service.compute_utilization(budget, spent)
    # Automatic alerts are evaluated on read so thresholds stay current.
    await alert_service.evaluate_budget_alerts(db, user_id, budget, utilization)
    base = BudgetResponse.model_validate(budget)
    return BudgetWithUtilization(**base.model_dump(), utilization=utilization)


@router.post(
    "",
    response_model=BudgetWithUtilization,
    status_code=status.HTTP_201_CREATED,
    summary="Create a budget",
    description="Overall budgets have category=null; category budgets name one category.",
)
async def create_budget(payload: BudgetCreate, current_user: CurrentUser, db: DbSession):
    budget = await budget_service.create_budget(db, current_user.id, payload)
    return await _budget_with_utilization(db, current_user.id, budget)


@router.get(
    "",
    response_model=list[BudgetWithUtilization],
    summary="List budgets",
)
async def list_budgets(current_user: CurrentUser, db: DbSession):
    budgets = await budget_service.list_budgets(db, current_user.id)
    return [await _budget_with_utilization(db, current_user.id, b) for b in budgets]


@router.get(
    "/{budget_id}",
    response_model=BudgetWithUtilization,
    summary="Get a budget with utilization",
)
async def get_budget(budget_id: UUID, current_user: CurrentUser, db: DbSession):
    budget = await budget_service.get_budget_owned(db, current_user.id, budget_id)
    return await _budget_with_utilization(db, current_user.id, budget)


@router.patch(
    "/{budget_id}",
    response_model=BudgetWithUtilization,
    summary="Update a budget",
)
async def update_budget(
    budget_id: UUID, payload: BudgetUpdate, current_user: CurrentUser, db: DbSession
):
    budget = await budget_service.update_budget(
        db, current_user.id, budget_id, payload
    )
    return await _budget_with_utilization(db, current_user.id, budget)


@router.delete(
    "/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a budget",
)
async def delete_budget(budget_id: UUID, current_user: CurrentUser, db: DbSession) -> None:
    await budget_service.delete_budget(db, current_user.id, budget_id)
