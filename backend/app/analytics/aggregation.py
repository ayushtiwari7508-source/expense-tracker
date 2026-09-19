"""Aggregation utilities built on Pandas DataFrames."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pandas as pd

from backend.app.models.expense import Expense


@dataclass(frozen=True)
class SummaryStats:
    """Immutable summary metrics for a set of expenses."""

    total_expenses: int
    total_amount: Decimal
    average_expense: Decimal
    highest_expense: Decimal | None
    lowest_expense: Decimal | None
    start_date: date
    end_date: date


def expenses_to_dataframe(expenses: list[Expense]) -> pd.DataFrame:
    """Convert expense ORM objects into a DataFrame.

    Monetary values are kept as Decimal (object dtype) to avoid
    floating-point arithmetic on money.
    """
    if not expenses:
        return pd.DataFrame(
            columns=["id", "amount", "category", "description",
                     "payment_method", "expense_date"]
        )
    return pd.DataFrame(
        [
            {
                "id": e.id,
                "amount": Decimal(e.amount),
                "category": e.category,
                "description": e.description,
                "payment_method": e.payment_method,
                "expense_date": e.expense_date,
            }
            for e in expenses
        ]
    )


def compute_summary(
    expenses: list[Expense], start_date: date, end_date: date
) -> SummaryStats:
    """Compute headline summary metrics for the given expenses."""
    if not expenses:
        return SummaryStats(
            total_expenses=0,
            total_amount=Decimal("0"),
            average_expense=Decimal("0"),
            highest_expense=None,
            lowest_expense=None,
            start_date=start_date,
            end_date=end_date,
        )

    df = expenses_to_dataframe(expenses)
    total = sum((Decimal(a) for a in df["amount"]), Decimal("0"))
    count = len(df)
    average = (total / Decimal(count)).quantize(Decimal("0.01"))
    return SummaryStats(
        total_expenses=count,
        total_amount=total.quantize(Decimal("0.01")),
        average_expense=average,
        highest_expense=Decimal(max(df["amount"], key=lambda a: Decimal(a))),
        lowest_expense=Decimal(min(df["amount"], key=lambda a: Decimal(a))),
        start_date=start_date,
        end_date=end_date,
    )


def aggregate_by_category(expenses: list[Expense]) -> list[dict]:
    """Aggregate spending per category with share of total (Pandas groupby)."""
    df = expenses_to_dataframe(expenses)
    if df.empty:
        return []

    grouped = df.groupby("category")["amount"].agg(["sum", "count"])
    grand_total = sum((Decimal(v) for v in grouped["sum"]), Decimal("0"))

    rows: list[dict] = []
    for category, row in grouped.iterrows():
        cat_total = Decimal(row["sum"])
        pct = float(cat_total / grand_total * 100) if grand_total > 0 else 0.0
        rows.append(
            {
                "category": str(category),
                "total": cat_total.quantize(Decimal("0.01")),
                "percentage": round(pct, 2),
                "count": int(row["count"]),
            }
        )
    rows.sort(key=lambda r: r["total"], reverse=True)
    return rows


def _period_label(d: date, granularity: str) -> str:
    if granularity == "daily":
        return d.isoformat()
    if granularity == "weekly":
        iso = d.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if granularity == "monthly":
        return f"{d.year}-{d.month:02d}"
    return f"{d.year}"


def aggregate_by_period(
    expenses: list[Expense], granularity: str
) -> list[dict]:
    """Aggregate spending per period (daily/weekly/monthly/yearly)."""
    df = expenses_to_dataframe(expenses)
    if df.empty:
        return []

    df["period"] = df["expense_date"].map(lambda d: _period_label(d, granularity))
    grouped = df.groupby("period")["amount"].agg(["sum", "count"])

    rows: list[dict] = []
    for period, row in grouped.iterrows():
        rows.append(
            {
                "period": str(period),
                "total": Decimal(row["sum"]).quantize(Decimal("0.01")),
                "count": int(row["count"]),
            }
        )
    rows.sort(key=lambda r: r["period"])
    return rows
