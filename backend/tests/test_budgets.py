"""Budget endpoint tests."""

from datetime import date

from tests.conftest import auth_header, make_budget_payload, register_and_login


async def _create(client, headers, **overrides):
    payload = make_budget_payload(**overrides)
    return await client.post("/api/v1/budgets", json=payload, headers=headers)


async def test_create_overall_budget(client):
    data = await register_and_login(client)
    response = await _create(client, auth_header(data), category=None, amount=20000)
    assert response.status_code == 201
    body = response.json()
    assert body["category"] is None
    assert body["amount"] == 20000
    assert "utilization" in body


async def test_create_category_budget(client):
    data = await register_and_login(client)
    response = await _create(client, auth_header(data))
    assert response.status_code == 201
    assert response.json()["category"] == "Food"


async def test_create_budget_invalid_dates(client):
    data = await register_and_login(client)
    response = await _create(
        client,
        auth_header(data),
        start=date(2026, 9, 30),
        end=date(2026, 9, 1),
    )
    assert response.status_code == 422


async def test_create_budget_invalid_threshold(client):
    data = await register_and_login(client)
    response = await _create(client, auth_header(data), threshold=150)
    assert response.status_code == 422


async def test_create_budget_negative_amount(client):
    data = await register_and_login(client)
    response = await _create(client, auth_header(data), amount=-1)
    assert response.status_code == 422


async def test_get_budget_with_utilization(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    budget = (await _create(client, headers, amount=100)).json()

    # Spend 50 within the budget window.
    await client.post(
        "/api/v1/expenses",
        json={
            "amount": 50,
            "category": "Food",
            "description": None,
            "payment_method": "UPI",
            "expense_date": "2026-09-15",
        },
        headers=headers,
    )

    response = await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers)
    body = response.json()
    util = body["utilization"]
    assert util["budget_amount"] == 100
    assert util["amount_spent"] == 50
    assert util["remaining_amount"] == 50
    assert util["utilization_percentage"] == 50.0
    assert util["status"] == "NORMAL"


async def test_utilization_warning_status(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    # threshold 80 → 84% utilisation is WARNING
    budget = (await _create(client, headers, amount=100, threshold=80)).json()
    await client.post(
        "/api/v1/expenses",
        json={
            "amount": 84,
            "category": "Food",
            "description": None,
            "payment_method": "UPI",
            "expense_date": "2026-09-15",
        },
        headers=headers,
    )
    body = (await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers)).json()
    assert body["utilization"]["status"] == "WARNING"
    assert body["utilization"]["utilization_percentage"] == 84.0


async def test_utilization_exceeded_status(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    budget = (await _create(client, headers, amount=100, threshold=80)).json()
    await client.post(
        "/api/v1/expenses",
        json={
            "amount": 150,
            "category": "Food",
            "description": None,
            "payment_method": "UPI",
            "expense_date": "2026-09-15",
        },
        headers=headers,
    )
    body = (await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers)).json()
    assert body["utilization"]["status"] == "EXCEEDED"
    assert body["utilization"]["remaining_amount"] == -50


async def test_overall_budget_spans_all_categories(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    budget = (await _create(client, headers, category=None, amount=100)).json()
    for category in ("Food", "Travel"):
        await client.post(
            "/api/v1/expenses",
            json={
                "amount": 30,
                "category": category,
                "description": None,
                "payment_method": "UPI",
                "expense_date": "2026-09-15",
            },
            headers=headers,
        )
    body = (await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers)).json()
    assert body["utilization"]["amount_spent"] == 60


async def test_update_budget(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    budget = (await _create(client, headers)).json()
    response = await client.patch(
        f"/api/v1/budgets/{budget['id']}",
        json={"amount": 8000, "alert_threshold": 90},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["amount"] == 8000
    assert body["alert_threshold"] == 90


async def test_update_budget_invalid_date_range(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    budget = (await _create(client, headers)).json()
    response = await client.patch(
        f"/api/v1/budgets/{budget['id']}",
        json={"end_date": "2026-08-01"},  # before start_date
        headers=headers,
    )
    assert response.status_code == 422


async def test_delete_budget(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    budget = (await _create(client, headers)).json()
    response = await client.delete(f"/api/v1/budgets/{budget['id']}", headers=headers)
    assert response.status_code == 204


async def test_budget_ownership_isolation(client):
    user_a = await register_and_login(client, email="ba@example.com")
    user_b = await register_and_login(client, email="bb@example.com")
    budget = (await _create(client, auth_header(user_a))).json()

    response = await client.get(
        f"/api/v1/budgets/{budget['id']}", headers=auth_header(user_b)
    )
    assert response.status_code == 404
    response = await client.delete(
        f"/api/v1/budgets/{budget['id']}", headers=auth_header(user_b)
    )
    assert response.status_code == 404


async def test_list_budgets_scoped_to_user(client):
    user_a = await register_and_login(client, email="la@example.com")
    user_b = await register_and_login(client, email="lb@example.com")
    await _create(client, auth_header(user_a))
    response = await client.get("/api/v1/budgets", headers=auth_header(user_b))
    assert response.json() == []


async def test_utilization_at_exactly_100_percent(client):
    """Boundary: 100% utilization is EXCEEDED (>= 100), remaining exactly 0."""
    data = await register_and_login(client, email="exact100@example.com")
    headers = auth_header(data)
    budget = (await _create(client, headers, amount=100, threshold=80)).json()
    await client.post(
        "/api/v1/expenses",
        json={
            "amount": 100,
            "category": "Food",
            "description": None,
            "payment_method": "UPI",
            "expense_date": "2026-09-15",
        },
        headers=headers,
    )
    util = (await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers)).json()[
        "utilization"
    ]
    assert util["utilization_percentage"] == 100.0
    assert util["remaining_amount"] == 0
    assert util["status"] == "EXCEEDED"


async def test_budget_window_includes_boundary_dates(client):
    """Only expenses inside [start_date, end_date] count — boundaries included."""
    data = await register_and_login(client, email="window@example.com")
    headers = auth_header(data)
    budget = (
        await _create(
            client,
            headers,
            amount=100,
            threshold=80,
            start=date(2026, 9, 10),
            end=date(2026, 9, 20),
        )
    ).json()
    # before window, first day, last day, after window
    for day, amount in ((9, 30), (10, 20), (20, 30), (21, 40)):
        await client.post(
            "/api/v1/expenses",
            json={
                "amount": amount,
                "category": "Food",
                "description": None,
                "payment_method": "UPI",
                "expense_date": f"2026-09-{day:02d}",
            },
            headers=headers,
        )
    util = (await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers)).json()[
        "utilization"
    ]
    assert util["amount_spent"] == 50  # 20 (start) + 30 (end); 30/40 outside excluded


async def test_zero_threshold_warns_on_any_spending(client):
    """Boundary: threshold=0 means any spending (>= 0%) is a WARNING."""
    data = await register_and_login(client, email="zerothresh@example.com")
    headers = auth_header(data)
    budget = (await _create(client, headers, amount=100, threshold=0)).json()
    await client.post(
        "/api/v1/expenses",
        json={
            "amount": 1,
            "category": "Food",
            "description": None,
            "payment_method": "UPI",
            "expense_date": "2026-09-15",
        },
        headers=headers,
    )
    util = (await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers)).json()[
        "utilization"
    ]
    assert util["status"] == "WARNING"


async def test_budget_update_ownership_isolation(client):
    """User B cannot PATCH User A's budget."""
    user_a = await register_and_login(client, email="bu-a@example.com")
    user_b = await register_and_login(client, email="bu-b@example.com")
    budget = (await _create(client, auth_header(user_a))).json()
    response = await client.patch(
        f"/api/v1/budgets/{budget['id']}",
        json={"amount": 1},
        headers=auth_header(user_b),
    )
    assert response.status_code == 404
