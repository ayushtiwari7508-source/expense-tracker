"""Time-series engine tests, independent of HTTP (QA spec section 27).

Datasets follow the QA matrix: constant, increasing, decreasing, single
point, empty, duplicate dates, duplicate amounts, and large spikes.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from backend.app.analytics.aggregation import aggregate_by_period
from backend.app.analytics.time_series import (
    build_time_series,
    detect_spending_spikes,
    statsmodels_trend_slope,
    trend_direction,
)
from backend.app.models.expense import Expense


def _expense(amount: str, day: int, month: int = 9, year: int = 2026) -> Expense:
    return Expense(
        id=uuid4(),
        user_id=uuid4(),
        amount=Decimal(amount),
        category="Food",
        description=None,
        payment_method="UPI",
        expense_date=date(year, month, day),
    )


class TestTrendDirection:
    def test_increasing(self):
        assert trend_direction([1, 2, 3, 4, 5]) == "increasing"

    def test_decreasing(self):
        assert trend_direction([5, 4, 3, 2, 1]) == "decreasing"

    def test_constant_is_stable(self):
        assert trend_direction([3, 3, 3, 3]) == "stable"

    def test_single_point_is_stable(self):
        assert trend_direction([42]) == "stable"

    def test_empty_is_stable(self):
        assert trend_direction([]) == "stable"

    def test_noise_within_threshold_is_stable(self):
        assert trend_direction([10, 10.3, 9.8, 10.1, 10.0]) == "stable"


class TestStatsmodelsTrendSlope:
    def test_positive_slope(self):
        slope = statsmodels_trend_slope([1, 2, 3, 4, 5])
        assert slope is not None
        assert abs(slope - 1.0) < 1e-6

    def test_negative_slope(self):
        slope = statsmodels_trend_slope([5, 4, 3, 2, 1])
        assert slope is not None
        assert abs(slope + 1.0) < 1e-6

    def test_too_few_points_returns_none(self):
        assert statsmodels_trend_slope([5]) is None


class TestBuildTimeSeries:
    def test_empty_returns_empty(self):
        assert build_time_series([], "daily") == []

    def test_daily_zero_fills_missing_days(self):
        """Missing days are explicit zeros, not invented values."""
        expenses = [_expense("100", 1), _expense("50", 5)]
        points = build_time_series(expenses, "daily")
        periods = [p["period"] for p in points]
        assert periods == ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05"]
        totals = {p["period"]: p["total"] for p in points}
        assert totals["2026-09-01"] == 100.0
        assert totals["2026-09-03"] == 0.0
        assert totals["2026-09-05"] == 50.0

    def test_single_expense_single_point(self):
        points = build_time_series([_expense("33.33", 10)], "daily")
        assert len(points) == 1
        assert points[0]["period"] == "2026-09-10"
        assert points[0]["total"] == 33.33
        assert points[0]["count"] == 1

    def test_duplicate_dates_are_summed(self):
        points = build_time_series([_expense("10", 2), _expense("15", 2)], "daily")
        assert len(points) == 1
        assert points[0]["total"] == 25.0
        assert points[0]["count"] == 2

    def test_duplicate_amounts_counted(self):
        points = build_time_series(
            [_expense("10", 2), _expense("10", 2), _expense("10", 2)], "daily"
        )
        assert points[0]["total"] == 30.0
        assert points[0]["count"] == 3

    def test_chronological_ordering(self):
        expenses = [_expense("10", d) for d in (9, 1, 5, 3)]
        periods = [p["period"] for p in build_time_series(expenses, "daily")]
        assert periods == sorted(periods)

    def test_monthly_aggregation(self):
        expenses = [_expense("100", 1), _expense("200", 20), _expense("400", 5, month=10)]
        points = build_time_series(expenses, "monthly")
        assert [p["period"] for p in points] == ["2026-09", "2026-10"]
        assert points[0]["total"] == 300.0
        assert points[1]["total"] == 400.0

    def test_yearly_aggregation(self):
        expenses = [
            _expense("100", 1, month=1),
            _expense("50", 1, month=6),
            _expense("25", 1, month=3),
            _expense("500", 1, month=12, year=2025),
        ]
        points = build_time_series(expenses, "yearly")
        assert [p["period"] for p in points] == ["2025", "2026"]
        assert points[0]["total"] == 500.0
        assert points[1]["total"] == 175.0

    def test_invalid_granularity_raises(self):
        try:
            build_time_series([_expense("1", 1)], "hourly")
        except ValueError:
            return
        raise AssertionError("expected ValueError for invalid granularity")

    def test_moving_average_window_larger_than_data_is_null(self):
        expenses = [_expense("10", d) for d in (1, 2, 3)]
        points = build_time_series(expenses, "daily", moving_average_window=7)
        assert all(p["moving_average"] is None for p in points)

    def test_moving_average_values(self):
        expenses = [_expense("10", 1), _expense("20", 2), _expense("30", 3)]
        points = build_time_series(expenses, "daily", moving_average_window=3)
        assert points[0]["moving_average"] is None
        assert points[1]["moving_average"] is None
        assert points[2]["moving_average"] == 20.0

    def test_deterministic_across_runs(self):
        expenses = [_expense("10", d) for d in (1, 2, 3, 4)]
        first = build_time_series(list(expenses), "daily")
        second = build_time_series(list(expenses), "daily")
        assert first == second


class TestSpendingSpikes:
    def test_spike_detected(self):
        expenses = [_expense("10", d) for d in range(1, 10)]
        expenses.append(_expense("1000", 10))
        spikes = detect_spending_spikes(expenses)
        assert spikes
        assert spikes[-1]["period"] == "2026-09-10"
        assert spikes[-1]["total"] == 1000.0

    def test_constant_spending_has_no_spikes(self):
        expenses = [_expense("10", d) for d in range(1, 12)]
        assert detect_spending_spikes(expenses) == []

    def test_empty_dataset(self):
        assert detect_spending_spikes([]) == []

    def test_single_point_no_spikes(self):
        assert detect_spending_spikes([_expense("10", 1)]) == []


class TestAggregateByPeriod:
    def test_weekly_boundaries(self):
        """ISO weeks: Sep 1 2026 (Tue) is W36; Sep 7 (Mon) starts W37."""
        expenses = [_expense("100", 1), _expense("100", 7), _expense("100", 8)]
        rows = aggregate_by_period(expenses, "weekly")
        assert [r["period"] for r in rows] == ["2026-W36", "2026-W37"]
        assert rows[0]["total"] == Decimal("100.00")
        assert rows[1]["total"] == Decimal("200.00")

    def test_daily_totals_exact(self):
        """Decimal arithmetic, not floats (QA spec §18)."""
        expenses = [_expense("10.10", 1), _expense("20.20", 1), _expense("30", 2)]
        rows = aggregate_by_period(expenses, "daily")
        assert rows[0]["total"] == Decimal("30.30")
        assert rows[1]["total"] == Decimal("30.00")
