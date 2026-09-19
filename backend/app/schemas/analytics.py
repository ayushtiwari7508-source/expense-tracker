"""Analytics schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from backend.app.schemas.common import Money


class SummaryResponse(BaseModel):
    total_expenses: int
    total_amount: Money
    average_expense: Money
    highest_expense: Money | None
    lowest_expense: Money | None
    current_period_spending: Money
    previous_period_spending: Money
    percentage_change: float | None
    start_date: date
    end_date: date


class CategoryAnalyticsItem(BaseModel):
    category: str
    total: Money
    percentage: float
    count: int


class TrendPoint(BaseModel):
    period: str
    total: Money
    count: int = 0


class TimeSeriesPoint(BaseModel):
    period: str
    total: float
    count: int
    moving_average: float | None = None


class TimeSeriesResponse(BaseModel):
    granularity: str
    points: list[TimeSeriesPoint]
    trend_direction: str
    percentage_change: float | None


class TopExpenseItem(BaseModel):
    id: UUID
    amount: Money
    category: str
    description: str | None
    expense_date: date
    rank: int


class Insight(BaseModel):
    type: str
    message: str


class InsightsResponse(BaseModel):
    generated_at: datetime
    insights: list[Insight]
