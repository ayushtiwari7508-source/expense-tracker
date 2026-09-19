"""Deterministic, factual spending insights.

No AI, no financial advice — only statements derived from the user's data.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from backend.app.analytics.aggregation import SummaryStats
from backend.app.schemas.budget import BudgetUtilization

INSIGHT_TYPES = {
    "category_share",
    "period_change",
    "highest_expense",
    "category_change",
    "budget_status",
}


@dataclass(frozen=True)
class InsightItem:
    """A single generated insight."""

    type: str
    message: str


def _money(value: Decimal) -> str:
    """Format money without floats: integer rupees with thousands separators."""
    q = Decimal(value).quantize(Decimal("1"))
    return f"₹{q:,.0f}"


def generate_insights(
    summary: SummaryStats,
    previous_summary: SummaryStats,
    category_rows: list[dict],
    budget_utilizations: list[tuple[Any, BudgetUtilization]],
) -> list[InsightItem]:
    """Produce deterministic factual insights from computed analytics."""
    insights: list[InsightItem] = []

    # 1. Top category share.
    if category_rows and summary.total_amount > 0:
        top = category_rows[0]
        insights.append(
            InsightItem(
                type="category_share",
                message=(
                    f"{top['category']} represents {top['percentage']:.0f}% "
                    f"of total spending ({_money(top['total'])})."
                ),
            )
        )

    # 2. Period-over-period change.
    prev_total = previous_summary.total_amount
    curr_total = summary.total_amount
    if prev_total > 0:
        change_pct = float((curr_total - prev_total) / prev_total * 100)
        direction = "more" if change_pct >= 0 else "less"
        insights.append(
            InsightItem(
                type="period_change",
                message=(
                    f"You spent {abs(change_pct):.0f}% {direction} this period "
                    f"than the previous period."
                ),
            )
        )

    # 3. Highest expense.
    if summary.highest_expense is not None:
        insights.append(
            InsightItem(
                type="highest_expense",
                message=f"Your highest expense was {_money(summary.highest_expense)}.",
            )
        )

    # 4. Largest category change vs previous period.
    prev_by_category: dict[str, Decimal] = {}
    if previous_summary.total_expenses > 0:
        # Callers pass only current-period rows; previous per-category totals
        # are recomputed by the service when available (see analytics_service).
        pass

    # 5. Budget status insights.
    for budget, utilization in budget_utilizations:
        scope = budget.category or "Overall"
        if utilization.status == "EXCEEDED":
            insights.append(
                InsightItem(
                    type="budget_status",
                    message=(
                        f"{scope} budget exceeded by "
                        f"{_money(utilization.amount_spent - utilization.budget_amount)}."
                    ),
                )
            )
        elif utilization.status == "WARNING":
            insights.append(
                InsightItem(
                    type="budget_status",
                    message=(
                        f"{scope} budget is at "
                        f"{utilization.utilization_percentage:.0f}% of its limit."
                    ),
                )
            )

    return insights


def add_category_change_insight(
    insights: list[InsightItem],
    current_rows: list[dict],
    previous_rows: list[dict],
) -> list[InsightItem]:
    """Append a factual category change insight when both periods have data."""
    if not previous_rows:
        return insights

    prev_totals = {r["category"]: r["total"] for r in previous_rows}
    curr_totals = {r["category"]: r["total"] for r in current_rows}

    # Pick the category with the largest absolute change.
    best_category, best_change = None, Decimal("0")
    for category, curr in curr_totals.items():
        prev = prev_totals.get(category, Decimal("0"))
        change = curr - prev
        if prev > 0 and abs(change) > abs(best_change):
            best_category, best_change = category, change

    if best_category is None or best_change == 0:
        return insights

    prev = prev_totals[best_category]
    pct = float(best_change / prev * 100)
    direction = "increased" if pct >= 0 else "decreased"
    insights.append(
        InsightItem(
            type="category_change",
            message=(
                f"{best_category} spending {direction} by {abs(pct):.0f}% "
                "compared with the previous period."
            ),
        )
    )
    return insights
