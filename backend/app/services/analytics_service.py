"""Analytics service: orchestrates the analytics engine for the API layer."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.analytics.aggregation import (
    aggregate_by_category,
    aggregate_by_period,
    compute_summary,
)
from backend.app.analytics.heap_analysis import top_n_expenses
from backend.app.analytics.insights import generate_insights
from backend.app.analytics.time_series import (
    build_time_series,
    trend_direction,
)
from backend.app.core.exceptions import ValidationError
from backend.app.models.expense import Expense
from backend.app.schemas.analytics import (
    CategoryAnalyticsItem,
    Insight,
    InsightsResponse,
    SummaryResponse,
    TimeSeriesPoint,
    TimeSeriesResponse,
    TopExpenseItem,
    TrendPoint,
)
from backend.app.schemas.budget import BudgetUtilization
from backend.app.services.budget_service import compute_utilization, spent_for_budget

GRANULARITIES = {"daily", "weekly", "monthly", "yearly"}


async def _load_expenses(
    db: AsyncSession,
    user_id: UUID,
    start_date: date | None,
    end_date: date | None,
) -> list[Expense]:
    """Load the user's expenses over an optional inclusive date range."""
    query = select(Expense).where(Expense.user_id == user_id)
    if start_date is not None:
        query = query.where(Expense.expense_date >= start_date)
    if end_date is not None:
        query = query.where(Expense.expense_date <= end_date)
    result = await db.execute(query.order_by(Expense.expense_date))
    return list(result.scalars().all())


def _resolve_range(
    start_date: date | None, end_date: date | None
) -> tuple[date, date]:
    """Resolve a default 30-day window ending today when no range is given."""
    if end_date is None and start_date is None:
        end = date.today()
        return end - timedelta(days=29), end
    if end_date is None:
        end = date.today()
    else:
        end = end_date
    if start_date is None:
        start = end - timedelta(days=29)
    else:
        start = start_date
    if start > end:
        raise ValidationError("start_date must be on or before end_date")
    return start, end


async def get_summary(
    db: AsyncSession,
    user_id: UUID,
    start_date: date | None,
    end_date: date | None,
) -> SummaryResponse:
    """Return headline spending metrics for a period with period-over-period change."""
    start, end = _resolve_range(start_date, end_date)
    expenses = await _load_expenses(db, user_id, start, end)
    summary = compute_summary(expenses, start, end)

    period_days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_days - 1)
    prev_expenses = await _load_expenses(db, user_id, prev_start, prev_end)
    prev_total = compute_summary(prev_expenses, prev_start, prev_end).total_amount

    current_total = summary.total_amount
    if prev_total > 0:
        pct_change = float((current_total - prev_total) / prev_total * 100)
    elif current_total > 0:
        pct_change = None  # no meaningful baseline
    else:
        pct_change = 0.0

    return SummaryResponse(
        total_expenses=summary.total_expenses,
        total_amount=summary.total_amount,
        average_expense=summary.average_expense,
        highest_expense=summary.highest_expense,
        lowest_expense=summary.lowest_expense,
        current_period_spending=current_total,
        previous_period_spending=prev_total,
        percentage_change=round(pct_change, 2) if pct_change is not None else None,
        start_date=start,
        end_date=end,
    )


async def get_category_analytics(
    db: AsyncSession,
    user_id: UUID,
    start_date: date | None,
    end_date: date | None,
) -> list[CategoryAnalyticsItem]:
    """Return spending aggregated by category with percentages."""
    start, end = _resolve_range(start_date, end_date)
    expenses = await _load_expenses(db, user_id, start, end)
    rows = aggregate_by_category(expenses)
    return [
        CategoryAnalyticsItem(category=r["category"], total=r["total"],
                              percentage=r["percentage"], count=r["count"])
        for r in rows
    ]


async def get_trends(
    db: AsyncSession,
    user_id: UUID,
    granularity: str,
    start_date: date | None,
    end_date: date | None,
) -> list[TrendPoint]:
    """Return per-period totals for the requested granularity."""
    if granularity not in GRANULARITIES:
        raise ValidationError(f"granularity must be one of {sorted(GRANULARITIES)}")
    start, end = _resolve_range(start_date, end_date)
    expenses = await _load_expenses(db, user_id, start, end)
    rows = aggregate_by_period(expenses, granularity)
    return [TrendPoint(period=r["period"], total=r["total"], count=r["count"]) for r in rows]


async def get_time_series(
    db: AsyncSession,
    user_id: UUID,
    granularity: str,
    start_date: date | None,
    end_date: date | None,
    moving_average_window: int = 7,
) -> TimeSeriesResponse:
    """Return an ECharts-friendly time series with moving average and trend."""
    if granularity not in GRANULARITIES:
        raise ValidationError(f"granularity must be one of {sorted(GRANULARITIES)}")
    start, end = _resolve_range(start_date, end_date)
    expenses = await _load_expenses(db, user_id, start, end)
    series = build_time_series(expenses, granularity, moving_average_window)

    totals = [p["total"] for p in series]
    first, last = (totals[0] if totals else 0.0), (totals[-1] if totals else 0.0)
    pct_change: float | None = None
    if first > 0:
        pct_change = round((last - first) / first * 100, 2)

    points = [
        TimeSeriesPoint(
            period=p["period"], total=p["total"], count=p["count"],
            moving_average=p.get("moving_average"),
        )
        for p in series
    ]
    return TimeSeriesResponse(
        granularity=granularity,
        points=points,
        trend_direction=trend_direction([p["total"] for p in series]),
        percentage_change=pct_change,
    )


async def get_top_expenses(
    db: AsyncSession,
    user_id: UUID,
    limit: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[TopExpenseItem]:
    """Return the user's largest expenses using the heap-based selector."""
    expenses = await _load_expenses(db, user_id, start_date, end_date)
    ranked = top_n_expenses(expenses, limit)
    return [
        TopExpenseItem(
            id=e.id,
            amount=e.amount,
            category=e.category,
            description=e.description,
            expense_date=e.expense_date,
            rank=i + 1,
        )
        for i, e in enumerate(ranked)
    ]


async def get_insights(
    db: AsyncSession,
    user_id: UUID,
    start_date: date | None,
    end_date: date | None,
) -> InsightsResponse:
    """Generate deterministic factual insights from the user's data."""

    start, end = _resolve_range(start_date, end_date)
    expenses = await _load_expenses(db, user_id, start, end)
    summary = compute_summary(expenses, start, end)

    period_days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_days - 1)
    prev_expenses = await _load_expenses(db, user_id, prev_start, prev_end)
    prev_summary = compute_summary(prev_expenses, prev_start, prev_end)

    # Per-category totals across both periods for category insights.
    cat_rows = aggregate_by_category(expenses)

    # Budget utilization for active budgets (for budget-related insights).
    from backend.app.models.budget import Budget

    budgets_result = await db.execute(
        select(Budget).where(
            Budget.user_id == user_id,
            Budget.start_date <= end,
            Budget.end_date >= start,
        )
    )
    budgets = list(budgets_result.scalars().all())
    budget_utils: list[tuple[Budget, BudgetUtilization]] = []
    for budget in budgets:
        spent = await spent_for_budget(db, user_id, budget)
        budget_utils.append((budget, compute_utilization(budget, spent)))

    messages = generate_insights(
        summary=summary,
        previous_summary=prev_summary,
        category_rows=cat_rows,
        budget_utilizations=budget_utils,
    )
    return InsightsResponse(
        generated_at=datetime.now(UTC),
        insights=[Insight(type=i.type, message=i.message) for i in messages],
    )


async def count_user_expenses(db: AsyncSession, user_id: UUID) -> int:
    """Count all expenses for a user."""
    result = await db.execute(
        select(func.count()).select_from(Expense).where(Expense.user_id == user_id)
    )
    return int(result.scalar_one())
