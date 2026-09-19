"""Time-series analysis for spending data.

Uses Pandas for aggregation, NumPy for statistics, and statsmodels for an
explainable linear trend — no black-box ML.
"""

from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd

from backend.app.analytics.aggregation import aggregate_by_period, expenses_to_dataframe
from backend.app.models.expense import Expense

GRANULARITIES = ("daily", "weekly", "monthly", "yearly")

# Periods (in granularity units) shown on the x-axis even when empty.
MAX_FILL_POINTS = 400


def _fill_daily_index(start: date, end: date) -> list[str]:
    """All daily labels in range (bounded)."""
    if (end - start).days + 1 > MAX_FILL_POINTS:
        return []
    return [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]


def build_time_series(
    expenses: list[Expense],
    granularity: str = "daily",
    moving_average_window: int = 7,
) -> list[dict]:
    """Build an ECharts-ready series of {period, total, count, moving_average}.

    Daily series are zero-filled across the requested range; for coarser
    granularities only periods that contain expenses are emitted (sorted).
    """
    if granularity not in GRANULARITIES:
        raise ValueError(f"granularity must be one of {GRANULARITIES}")

    df = expenses_to_dataframe(expenses)
    if df.empty:
        return []

    if granularity == "daily":
        df = df.set_index("expense_date")
        # Sum Decimals per day via groupby on the date index.
        daily = df.groupby(level=0)["amount"].agg(
            [("total", lambda s: sum((Decimal(v) for v in s), Decimal("0"))),
             ("count", "size")]
        )
        daily.index = pd.to_datetime(daily.index)
        daily = daily.sort_index()

        full_index = None
        if len(daily) > 1:
            first, last = daily.index.min(), daily.index.max()
            if (last - first).days + 1 <= MAX_FILL_POINTS:
                full_index = pd.date_range(first, last, freq="D")
        if full_index is not None:
            daily = daily.reindex(full_index)
            daily["total"] = daily["total"].fillna(Decimal("0"))
            daily["count"] = daily["count"].fillna(0).astype(int)

        totals = np.array([Decimal(t) for t in daily["total"]], dtype=float)
        ma = _moving_average(totals, moving_average_window)
        return [
            {
                "period": idx.strftime("%Y-%m-%d"),
                "total": round(float(t), 2),
                "count": int(c),
                "moving_average": (round(float(m), 2) if m is not None and not np.isnan(m) else None),
            }
            for idx, t, c, m in zip(daily.index, daily["total"], daily["count"], ma)
        ]

    # Coarser granularities: reuse the period aggregation (Decimal-safe).
    rows = aggregate_by_period(expenses, granularity)
    totals = np.array([float(r["total"]) for r in rows], dtype=float)
    ma = _moving_average(totals, moving_average_window)
    return [
        {
            "period": r["period"],
            "total": float(r["total"]),
            "count": r["count"],
            "moving_average": (round(float(m), 2) if m is not None and not np.isnan(m) else None),
        }
        for r, m in zip(rows, ma)
    ]


def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    """Simple moving average; leading values before the window are NaN."""
    if window <= 1 or values.size == 0 or window > values.size:
        return np.full(values.shape, np.nan)
    kernel = np.ones(window) / window
    smoothed = np.convolve(values, kernel, mode="valid")
    return np.concatenate([np.full(window - 1, np.nan), smoothed])


def trend_direction(values: list[float]) -> str:
    """Classify trend direction from a linear fit slope (explainable).

    Returns "increasing", "decreasing", or "stable" using a 5% relative
    slope threshold against the mean level.
    """
    arr = np.asarray(values, dtype=float)
    if arr.size < 2:
        return "stable"
    x = np.arange(arr.size, dtype=float)
    slope = float(np.polyfit(x, arr, 1)[0])
    mean_level = float(np.mean(np.abs(arr)))
    if mean_level == 0:
        return "stable"
    relative_slope = slope / mean_level
    if relative_slope > 0.05:
        return "increasing"
    if relative_slope < -0.05:
        return "decreasing"
    return "stable"


def detect_spending_spikes(
    expenses: list[Expense],
    window: int = 7,
    z_threshold: float = 2.0,
) -> list[dict]:
    """Detect spending spike days using a rolling mean/std z-score.

    Explainable rule: a day is a spike when its total exceeds the rolling
    mean of the surrounding ``window`` days by more than ``z_threshold``
    rolling standard deviations. Returns day labels with their z-scores.
    """
    if not expenses:
        return []

    df = expenses_to_dataframe(expenses)
    df = df.set_index("expense_date")
    daily = df.groupby(level=0)["amount"].agg(
        [("total", lambda s: sum((Decimal(v) for v in s), Decimal("0"))),
         ("count", "size")]
    )
    daily.index = pd.to_datetime(daily.index)
    daily = daily.sort_index()

    totals = np.array([float(t) for t in daily["total"]], dtype=float)
    series = pd.Series(totals, index=daily.index)
    rolling_mean = series.rolling(window, min_periods=3).mean()
    rolling_std = series.rolling(window, min_periods=3).std()

    spikes: list[dict] = []
    for idx, value in series.items():
        mean = rolling_mean.loc[idx]
        std = rolling_std.loc[idx]
        if pd.isna(mean) or pd.isna(std) or std == 0:
            continue
        z = float((value - mean) / std)
        if z >= z_threshold:
            spikes.append({"period": idx.strftime("%Y-%m-%d"), "total": round(float(value), 2), "z_score": round(z, 2)})
    return spikes


def statsmodels_trend_slope(values: list[float]) -> float | None:
    """OLS slope via statsmodels for an explainable trend estimate."""
    try:
        import statsmodels.api as sm

        arr = np.asarray(values, dtype=float)
        if arr.size < 2:
            return None
        x = np.arange(arr.size, dtype=float)
        model = sm.OLS(arr, sm.add_constant(x)).fit()
        return float(model.params[1])
    except Exception:  # pragma: no cover - statsmodels optional at runtime
        return None
