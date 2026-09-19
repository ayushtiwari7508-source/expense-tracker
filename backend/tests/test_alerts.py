"""Alert endpoint tests."""

from tests.conftest import auth_header, register_and_login


async def _setup_budget_with_spending(client, headers, amount_spent, budget_amount=100, threshold=80):
    budget_response = await client.post(
        "/api/v1/budgets",
        json={
            "category": "Food",
            "amount": budget_amount,
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
            "alert_threshold": threshold,
        },
        headers=headers,
    )
    await client.post(
        "/api/v1/expenses",
        json={
            "amount": amount_spent,
            "category": "Food",
            "description": None,
            "payment_method": "UPI",
            "expense_date": "2026-09-15",
        },
        headers=headers,
    )
    return budget_response.json()


async def test_warning_alert_generated(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    budget = await _setup_budget_with_spending(client, headers, amount_spent=84)
    # Reading the budget evaluates thresholds.
    await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers)

    response = await client.get("/api/v1/alerts", headers=headers)
    body = response.json()
    warnings = [a for a in body["items"] if a["type"] == "warning"]
    assert len(warnings) == 1
    assert "Food" in warnings[0]["message"]
    assert body["unread_count"] == 1


async def test_exceeded_alert_generated(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    budget = await _setup_budget_with_spending(client, headers, amount_spent=150)
    await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers)

    response = await client.get("/api/v1/alerts", headers=headers)
    items = response.json()["items"]
    exceeded = [a for a in items if a["type"] == "exceeded"]
    assert len(exceeded) == 1
    assert "exceeded" in exceeded[0]["message"].lower()


async def test_no_duplicate_alerts(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    budget = await _setup_budget_with_spending(client, headers, amount_spent=84)
    for _ in range(3):
        await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers)

    response = await client.get("/api/v1/alerts", headers=headers)
    warnings = [a for a in response.json()["items"] if a["type"] == "warning"]
    assert len(warnings) == 1


async def test_no_alert_below_threshold(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    budget = await _setup_budget_with_spending(client, headers, amount_spent=50)
    await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers)

    response = await client.get("/api/v1/alerts", headers=headers)
    assert response.json()["items"] == []


async def test_mark_alert_read(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    budget = await _setup_budget_with_spending(client, headers, amount_spent=120)
    await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers)

    alerts = (await client.get("/api/v1/alerts", headers=headers)).json()["items"]
    alert_id = alerts[0]["id"]
    response = await client.patch(f"/api/v1/alerts/{alert_id}/read", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_read"] is True

    body = (await client.get("/api/v1/alerts", headers=headers)).json()
    assert body["unread_count"] == 0


async def test_mark_all_read(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    # Two budgets exceeding → two alerts.
    b1 = await _setup_budget_with_spending(client, headers, amount_spent=120)
    await client.get(f"/api/v1/budgets/{b1['id']}", headers=headers)
    b2 = (
        await client.post(
            "/api/v1/budgets",
            json={
                "category": "Travel",
                "amount": 100,
                "start_date": "2026-09-01",
                "end_date": "2026-09-30",
                "alert_threshold": 80,
            },
            headers=headers,
        )
    ).json()
    await client.post(
        "/api/v1/expenses",
        json={
            "amount": 200,
            "category": "Travel",
            "description": None,
            "payment_method": "UPI",
            "expense_date": "2026-09-16",
        },
        headers=headers,
    )
    await client.get(f"/api/v1/budgets/{b2['id']}", headers=headers)

    response = await client.patch("/api/v1/alerts/read-all", headers=headers)
    assert response.status_code == 200

    body = (await client.get("/api/v1/alerts", headers=headers)).json()
    assert body["unread_count"] == 0
    assert all(a["is_read"] for a in body["items"])


async def test_alert_ownership_isolation(client):
    user_a = await register_and_login(client, email="aa@example.com")
    user_b = await register_and_login(client, email="ab@example.com")
    headers_a = auth_header(user_a)
    budget = await _setup_budget_with_spending(client, headers_a, amount_spent=120)
    await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers_a)

    alerts_a = (await client.get("/api/v1/alerts", headers=headers_a)).json()["items"]
    assert len(alerts_a) == 1

    # User B sees no alerts and cannot mark A's alert read.
    body_b = (await client.get("/api/v1/alerts", headers=auth_header(user_b))).json()
    assert body_b["items"] == []
    response = await client.patch(
        f"/api/v1/alerts/{alerts_a[0]['id']}/read", headers=auth_header(user_b)
    )
    assert response.status_code == 404


async def test_alert_exactly_at_threshold(client):
    """Boundary: utilization == threshold (50% vs 50%) generates a warning."""
    data = await register_and_login(client)
    headers = auth_header(data)
    budget = await _setup_budget_with_spending(
        client, headers, amount_spent=50, budget_amount=100, threshold=50
    )
    await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers)

    items = (await client.get("/api/v1/alerts", headers=headers)).json()["items"]
    warnings = [a for a in items if a["type"] == "warning"]
    assert len(warnings) == 1
    assert warnings[0]["budget_id"] == budget["id"]


async def test_exceeded_alert_at_exactly_100_percent(client):
    """Boundary: 100% utilization yields EXCEEDED, not WARNING."""
    data = await register_and_login(client)
    headers = auth_header(data)
    budget = await _setup_budget_with_spending(
        client, headers, amount_spent=100, budget_amount=100, threshold=80
    )
    await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers)

    items = (await client.get("/api/v1/alerts", headers=headers)).json()["items"]
    assert len(items) == 1
    assert items[0]["type"] == "exceeded"


async def test_mark_already_read_is_idempotent(client):
    """Marking a read alert read again succeeds and changes nothing."""
    data = await register_and_login(client)
    headers = auth_header(data)
    budget = await _setup_budget_with_spending(client, headers, amount_spent=120)
    await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers)

    alert_id = (await client.get("/api/v1/alerts", headers=headers)).json()["items"][0]["id"]
    first = await client.patch(f"/api/v1/alerts/{alert_id}/read", headers=headers)
    assert first.status_code == 200
    second = await client.patch(f"/api/v1/alerts/{alert_id}/read", headers=headers)
    assert second.status_code == 200
    assert second.json()["is_read"] is True

    body = (await client.get("/api/v1/alerts", headers=headers)).json()
    assert body["unread_count"] == 0
    assert len(body["items"]) == 1  # no duplicate alert was created


async def test_alerts_scoped_to_user_via_read_all(client):
    """User B's mark-all-read cannot touch User A's alerts."""
    user_a = await register_and_login(client, email="ra-a@example.com")
    user_b = await register_and_login(client, email="ra-b@example.com")
    headers_a = auth_header(user_a)
    budget = await _setup_budget_with_spending(client, headers_a, amount_spent=120)
    await client.get(f"/api/v1/budgets/{budget['id']}", headers=headers_a)

    response = await client.patch("/api/v1/alerts/read-all", headers=auth_header(user_b))
    assert response.status_code == 200

    body_a = (await client.get("/api/v1/alerts", headers=headers_a)).json()
    assert body_a["unread_count"] == 1  # A's alert is untouched by B's read-all
