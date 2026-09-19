"""Analytics routes."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from backend.app.api.deps import CurrentUser, DbSession
from backend.app.schemas.analytics import (
    CategoryAnalyticsItem,
    InsightsResponse,
    SummaryResponse,
    TimeSeriesResponse,
    TopExpenseItem,
    TrendPoint,
)
from backend.app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/summary",
    response_model=SummaryResponse,
    summary="Spending summary",
    description="Headline metrics with previous-period comparison.",
)
async def summary(
    current_user: CurrentUser,
    db: DbSession,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> SummaryResponse:
    return await analytics_service.get_summary(db, current_user.id, start_date, end_date)


@router.get(
    "/categories",
    response_model=list[CategoryAnalyticsItem],
    summary="Spending by category",
)
async def categories(
    current_user: CurrentUser,
    db: DbSession,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> list[CategoryAnalyticsItem]:
    return await analytics_service.get_category_analytics(
        db, current_user.id, start_date, end_date
    )


@router.get(
    "/trends",
    response_model=list[TrendPoint],
    summary="Spending trends",
    description="Per-period totals for daily/weekly/monthly/yearly granularity.",
)
async def trends(
    current_user: CurrentUser,
    db: DbSession,
    granularity: Annotated[str, Query(pattern="^(daily|weekly|monthly|yearly)$")] = "daily",
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> list[TrendPoint]:
    return await analytics_service.get_trends(
        db, current_user.id, granularity, start_date, end_date
    )


@router.get(
    "/time-series",
    response_model=TimeSeriesResponse,
    summary="Time series (ECharts-ready)",
)
async def time_series(
    current_user: CurrentUser,
    db: DbSession,
    granularity: Annotated[str, Query(pattern="^(daily|weekly|monthly|yearly)$")] = "daily",
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    moving_average_window: Annotated[int, Query(ge=2, le=90)] = 7,
) -> TimeSeriesResponse:
    return await analytics_service.get_time_series(
        db, current_user.id, granularity, start_date, end_date, moving_average_window
    )


@router.get(
    "/top-expenses",
    response_model=list[TopExpenseItem],
    summary="Top N expenses (heap-based)",
    description="Largest expenses selected with a heap (O(n log k)).",
)
async def top_expenses(
    current_user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> list[TopExpenseItem]:
    return await analytics_service.get_top_expenses(
        db, current_user.id, limit, start_date, end_date
    )


@router.get(
    "/insights",
    response_model=InsightsResponse,
    summary="Factual spending insights",
)
async def insights(
    current_user: CurrentUser,
    db: DbSession,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> InsightsResponse:
    return await analytics_service.get_insights(db, current_user.id, start_date, end_date)
