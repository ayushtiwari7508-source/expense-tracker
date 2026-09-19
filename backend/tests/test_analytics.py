"""Analytics endpoint and engine tests."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from backend.app.analytics.heap_analysis import MaxHeap, top_n_expenses, top_n_expenses_heap_class
from backend.app.analytics.time_series import detect_spending_spikes, trend_direction
from backend.app.models.expense import Expense
from tests.conftest import auth_header, register_and_login


def _fake_expense(amount: str, category: str = "Food", day: int = 1) -> Expense:
    return Expense(
        id=uuid4(),
        user_id=uuid4(),
        amount=Decimal(amount),
        category=category,
        description=None,
        payment_method="UPI",
        expense_date=date(2026, 9, day),
    )


# ---------------------------------------------------------------- Heap (DSA)


class TestMaxHeap:
    def test_push_and_pop_order(self):
        heap = MaxHeap()
        for amount in ("10", "50", "30", "99", "1"):
            heap.push(Decimal(amount), amount)
        popped = [heap.pop() for _ in range(len(heap))]
        assert popped == ["99", "50", "30", "10", "1"]

    def test_peek(self):
        heap = MaxHeap()
        heap.push(Decimal("5"), "five")
        heap.push(Decimal("9"), "nine")
        assert heap.peek() == "nine"
        assert len(heap) == 2

    def test_pop_empty(self):
        assert MaxHeap().pop() is None

    def test_descending_property(self):
        heap = MaxHeap()
        for i in range(100, 0, -1):
            heap.push(Decimal(i), i)
        out = []
        while not heap.is_empty():
            out.append(heap.pop())
        assert out == sorted(out, reverse=True)


class TestTopNExpenses:
    def test_heapq_top_n(self):
        expenses = [_fake_expense(a) for a in ("10", "500", "50", "300", "900")]
        top = top_n_expenses(expenses, 3)
        assert [str(e.amount) for e in top] == ["900", "500", "300"]

    def test_heapq_top_n_larger_than_list(self):
        expenses = [_fake_expense("7"), _fake_expense("3")]
        assert len(top_n_expenses(expenses, 10)) == 2

    def test_heapq_top_n_zero_or_empty(self):
        assert top_n_expenses([], 5) == []
        assert top_n_expenses([_fake_expense("1")], 0) == []

    def test_maxheap_class_top_n_matches(self):
        expenses = [_fake_expense(a) for a in ("12", "44", "7", "99")]
        via_class = top_n_expenses_heap_class(expenses, 2)
        via_heapq = top_n_expenses(expenses, 2)
        assert [e.amount for e in via_class] == [e.amount for e in via_heapq]

    def test_not_plain_sorted_call(self):
        """Guard: implementation must be heap-based, not sorted()."""
        import inspect

        from backend.app.analytics import heap_analysis as mod

        source = inspect.getsource(mod.top_n_expenses)
        assert "sorted(" not in source


# ------------------------------------------------------------ Time series


class TestTimeSeriesUtils:
    def test_trend_direction(self):
        assert trend_direction([1, 2, 3, 4, 5]) == "increasing"
        assert trend_direction([5, 4, 3, 2, 1]) == "decreasing"
        assert trend_direction([3, 3, 3, 3]) == "stable"
        assert trend_direction([1]) == "stable"

    def test_spending_spikes(self):
        expenses = [_fake_expense("10", day=d) for d in range(1, 10)]
        expenses.append(_fake_expense("1000", day=10))
        spikes = detect_spending_spikes(expenses)
        assert len(spikes) >= 1
        assert spikes[-1]["period"] == "2026-09-10"


# ------------------------------------------------------------ API endpoints


async def _seed_expenses(client, headers):
    rows = [
        ("250.50", "Food", "Dinner", "2026-09-16"),
        ("500", "Rent", "Monthly rent", "2026-09-01"),
        ("80", "Travel", "Taxi", "2026-09-02"),
        ("1200", "Shopping", "Clothes", "2026-08-20"),
        ("45.25", "Food", "Lunch", "2026-09-10"),
    ]
    for amount, category, description, expense_date in rows:
        await client.post(
            "/api/v1/expenses",
            json={
                "amount": float(amount),
                "category": category,
                "description": description,
                "payment_method": "UPI",
                "expense_date": expense_date,
            },
            headers=headers,
        )


async def test_summary(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    await _seed_expenses(client, headers)

    response = await client.get(
        "/api/v1/analytics/summary?start_date=2026-09-01&end_date=2026-09-30",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_expenses"] == 4
    assert body["total_amount"] == 875.75
    assert body["highest_expense"] == 500
    assert body["lowest_expense"] == 45.25
    assert body["average_expense"] == 218.94


async def test_summary_percentage_change(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    # Current period: 100; previous period: 200 → -50%.
    await client.post(
        "/api/v1/expenses",
        json={
            "amount": 100, "category": "Other", "description": None,
            "payment_method": "UPI", "expense_date": "2026-09-15",
        },
        headers=headers,
    )
    await client.post(
        "/api/v1/expenses",
        json={
            "amount": 200, "category": "Other", "description": None,
            "payment_method": "UPI", "expense_date": "2026-08-15",
        },
        headers=headers,
    )
    response = await client.get(
        "/api/v1/analytics/summary?start_date=2026-09-01&end_date=2026-09-30",
        headers=headers,
    )
    body = response.json()
    assert body["current_period_spending"] == 100
    assert body["previous_period_spending"] == 200
    assert body["percentage_change"] == -50.0


async def test_categories(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    await _seed_expenses(client, headers)

    response = await client.get(
        "/api/v1/analytics/categories?start_date=2026-08-01&end_date=2026-09-30",
        headers=headers,
    )
    assert response.status_code == 200
    rows = response.json()
    assert rows[0]["category"] == "Shopping"  # 1200 is the largest
    total_pct = sum(r["percentage"] for r in rows)
    assert 99.0 <= total_pct <= 101.0


async def test_trends_monthly(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    await _seed_expenses(client, headers)

    response = await client.get(
        "/api/v1/analytics/trends?granularity=monthly&start_date=2026-08-01&end_date=2026-09-30",
        headers=headers,
    )
    assert response.status_code == 200
    rows = response.json()
    assert [r["period"] for r in rows] == ["2026-08", "2026-09"]
    assert rows[0]["total"] == 1200


async def test_trends_invalid_granularity(client):
    data = await register_and_login(client)
    response = await client.get(
        "/api/v1/analytics/trends?granularity=hourly", headers=auth_header(data)
    )
    assert response.status_code == 422


async def test_time_series_daily(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    await _seed_expenses(client, headers)

    response = await client.get(
        "/api/v1/analytics/time-series?granularity=daily&start_date=2026-09-01&end_date=2026-09-20",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["granularity"] == "daily"
    assert len(body["points"]) >= 4
    assert body["points"][0]["period"] == "2026-09-01"
    # Zero-filled days exist (no expenses on 09-03 etc.).
    zero_days = [p for p in body["points"] if p["total"] == 0]
    assert zero_days


async def test_top_expenses(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    await _seed_expenses(client, headers)

    response = await client.get(
        "/api/v1/analytics/top-expenses?limit=3&start_date=2026-08-01&end_date=2026-09-30",
        headers=headers,
    )
    assert response.status_code == 200
    items = response.json()
    amounts = [i["amount"] for i in items]
    assert amounts == [1200, 500, 250.5]
    assert items[0]["rank"] == 1
    assert items[0]["category"] == "Shopping"


async def test_top_expenses_limit_validation(client):
    data = await register_and_login(client)
    response = await client.get(
        "/api/v1/analytics/top-expenses?limit=1000", headers=auth_header(data)
    )
    assert response.status_code == 422


async def test_insights(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    await _seed_expenses(client, headers)

    response = await client.get(
        "/api/v1/analytics/insights?start_date=2026-09-01&end_date=2026-09-30",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    messages = [i["message"] for i in body["insights"]]
    assert any("Your highest expense was" in m for m in messages)
    assert any("%" in m for m in messages)


async def test_analytics_require_auth(client):
    for path in (
        "/api/v1/analytics/summary",
        "/api/v1/analytics/categories",
        "/api/v1/analytics/trends",
        "/api/v1/analytics/time-series",
        "/api/v1/analytics/top-expenses",
        "/api/v1/analytics/insights",
    ):
        response = await client.get(path)
        assert response.status_code == 401, path


async def test_analytics_user_isolation(client):
    """User B's analytics must not include User A's expenses."""
    user_a = await register_and_login(client, email="an-a@example.com")
    await _seed_expenses(client, auth_header(user_a))

    user_b = await register_and_login(client, email="an-b@example.com")
    headers_b = auth_header(user_b)
    response = await client.get(
        "/api/v1/analytics/summary?start_date=2026-08-01&end_date=2026-09-30",
        headers=headers_b,
    )
    body = response.json()
    assert body["total_expenses"] == 0
    assert body["total_amount"] == 0


async def test_summary_empty_dataset(client):
    data = await register_and_login(client, email="empty@example.com")
    response = await client.get(
        "/api/v1/analytics/summary?start_date=2026-09-01&end_date=2026-09-30",
        headers=auth_header(data),
    )
    body = response.json()
    assert body["total_expenses"] == 0
    assert body["total_amount"] == 0
    assert body["highest_expense"] is None
    assert body["lowest_expense"] is None


async def test_analytics_empty_surfaces(client):
    """Empty data must yield empty results, never fake values."""
    data = await register_and_login(client, email="noexp@example.com")
    headers = auth_header(data)
    qs = "start_date=2026-09-01&end_date=2026-09-30"
    assert (await client.get(f"/api/v1/analytics/categories?{qs}", headers=headers)).json() == []
    assert (
        await client.get(f"/api/v1/analytics/time-series?granularity=daily&{qs}", headers=headers)
    ).json()["points"] == []
    assert (
        await client.get(f"/api/v1/analytics/trends?granularity=monthly&{qs}", headers=headers)
    ).json() == []
    assert (await client.get(f"/api/v1/analytics/top-expenses?limit=5&{qs}", headers=headers)).json() == []


async def test_summary_boundary_dates(client):
    """Expenses exactly on start_date and end_date are included."""
    data = await register_and_login(client, email="bound@example.com")
    headers = auth_header(data)
    for expense_date, amount in (("2026-08-31", 5), ("2026-09-01", 10), ("2026-09-30", 20)):
        await client.post(
            "/api/v1/expenses",
            json={
                "amount": amount,
                "category": "Food",
                "description": None,
                "payment_method": "UPI",
                "expense_date": expense_date,
            },
            headers=headers,
        )
    body = (
        await client.get(
            "/api/v1/analytics/summary?start_date=2026-09-01&end_date=2026-09-30",
            headers=headers,
        )
    ).json()
    assert body["total_expenses"] == 2
    assert body["total_amount"] == 30


async def test_top_expenses_duplicate_amounts(client):
    """Equal amounts are ranked deterministically; count is preserved."""
    data = await register_and_login(client, email="dupamts@example.com")
    headers = auth_header(data)
    for expense_date in ("2026-09-01", "2026-09-02"):
        await client.post(
            "/api/v1/expenses",
            json={
                "amount": 50,
                "category": "Food",
                "description": None,
                "payment_method": "UPI",
                "expense_date": expense_date,
            },
            headers=headers,
        )
    await client.post(
        "/api/v1/expenses",
        json={
            "amount": 75,
            "category": "Travel",
            "description": None,
            "payment_method": "UPI",
            "expense_date": "2026-09-03",
        },
        headers=headers,
    )
    items = (
        await client.get(
            "/api/v1/analytics/top-expenses?limit=3&start_date=2026-09-01&end_date=2026-09-30",
            headers=headers,
        )
    ).json()
    assert [i["amount"] for i in items] == [75, 50, 50]
    assert [i["rank"] for i in items] == [1, 2, 3]


async def test_expense_consistency_across_analytics(client):
    """QA §29: a created expense appears in every analytics surface, and
    disappears from all of them after deletion — no stale data."""
    data = await register_and_login(client, email="cons@example.com")
    headers = auth_header(data)
    created = (
        await client.post(
            "/api/v1/expenses",
            json={
                "amount": 10.25,
                "category": "Food",
                "description": "consistency probe",
                "payment_method": "UPI",
                "expense_date": "2026-05-15",
            },
            headers=headers,
        )
    ).json()

    qs = "start_date=2026-05-01&end_date=2026-05-31"
    summary = (await client.get(f"/api/v1/analytics/summary?{qs}", headers=headers)).json()
    assert summary["total_amount"] == 10.25

    categories = (await client.get(f"/api/v1/analytics/categories?{qs}", headers=headers)).json()
    assert categories[0]["category"] == "Food"
    assert categories[0]["total"] == 10.25

    trends = (
        await client.get(f"/api/v1/analytics/trends?granularity=monthly&{qs}", headers=headers)
    ).json()
    assert trends[0]["total"] == 10.25

    ts = (
        await client.get(f"/api/v1/analytics/time-series?granularity=daily&{qs}", headers=headers)
    ).json()
    day = next(p for p in ts["points"] if p["period"] == "2026-05-15")
    assert day["total"] == 10.25

    top = (
        await client.get(f"/api/v1/analytics/top-expenses?limit=5&{qs}", headers=headers)
    ).json()
    assert [t["amount"] for t in top] == [10.25]

    # Delete → every surface must drop the expense.
    assert (await client.delete(f"/api/v1/expenses/{created['id']}", headers=headers)).status_code == 204
    summary = (await client.get(f"/api/v1/analytics/summary?{qs}", headers=headers)).json()
    assert summary["total_expenses"] == 0 and summary["total_amount"] == 0
    assert (await client.get(f"/api/v1/analytics/categories?{qs}", headers=headers)).json() == []
    trends = (
        await client.get(f"/api/v1/analytics/trends?granularity=monthly&{qs}", headers=headers)
    ).json()
    assert trends == []
    ts = (
        await client.get(f"/api/v1/analytics/time-series?granularity=daily&{qs}", headers=headers)
    ).json()
    assert ts["points"] == []
    top = (
        await client.get(f"/api/v1/analytics/top-expenses?limit=5&{qs}", headers=headers)
    ).json()
    assert top == []
