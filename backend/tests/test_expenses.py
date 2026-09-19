"""Expense endpoint tests."""

from datetime import date

from tests.conftest import auth_header, make_expense_payload, register_and_login


async def _create(client, headers, **overrides):
    payload = make_expense_payload(**overrides)
    return await client.post("/api/v1/expenses", json=payload, headers=headers)


async def test_create_expense(client):
    data = await register_and_login(client)
    response = await _create(client, auth_header(data))
    assert response.status_code == 201
    body = response.json()
    assert body["category"] == "Food"
    assert body["amount"] == 250.5
    assert body["expense_date"] == "2026-09-16"


async def test_create_expense_invalid_amount(client):
    data = await register_and_login(client)
    response = await _create(client, auth_header(data), amount=-5)
    assert response.status_code == 422


async def test_create_expense_invalid_category(client):
    data = await register_and_login(client)
    response = await _create(client, auth_header(data), category="Crypto")
    assert response.status_code == 422


async def test_create_expense_invalid_payment_method(client):
    data = await register_and_login(client)
    response = await _create(client, auth_header(data), payment_method="Barter")
    assert response.status_code == 422


async def test_create_requires_auth(client):
    response = await client.post("/api/v1/expenses", json=make_expense_payload())
    assert response.status_code == 401


async def test_get_expense_by_id(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    created = (await _create(client, headers)).json()
    response = await client.get(f"/api/v1/expenses/{created['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_missing_expense_404(client):
    data = await register_and_login(client)
    response = await client.get(
        "/api/v1/expenses/00000000-0000-0000-0000-000000000000",
        headers=auth_header(data),
    )
    assert response.status_code == 404


async def test_update_expense(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    created = (await _create(client, headers)).json()
    response = await client.patch(
        f"/api/v1/expenses/{created['id']}",
        json={"amount": 99.99, "description": "Updated"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["amount"] == 99.99
    assert body["description"] == "Updated"
    assert body["category"] == "Food"  # unchanged


async def test_delete_expense(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    created = (await _create(client, headers)).json()
    response = await client.delete(f"/api/v1/expenses/{created['id']}", headers=headers)
    assert response.status_code == 204
    response = await client.get(f"/api/v1/expenses/{created['id']}", headers=headers)
    assert response.status_code == 404


async def test_ownership_isolation(client):
    """User B must never read User A's expense by ID."""
    user_a = await register_and_login(client, email="a@example.com")
    user_b = await register_and_login(client, email="b@example.com")

    created = (await _create(client, auth_header(user_a))).json()

    response = await client.get(
        f"/api/v1/expenses/{created['id']}", headers=auth_header(user_b)
    )
    assert response.status_code == 404

    response = await client.patch(
        f"/api/v1/expenses/{created['id']}",
        json={"amount": 1},
        headers=auth_header(user_b),
    )
    assert response.status_code == 404

    response = await client.delete(
        f"/api/v1/expenses/{created['id']}", headers=auth_header(user_b)
    )
    assert response.status_code == 404


async def test_list_filters_by_category(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    await _create(client, headers, category="Food")
    await _create(client, headers, category="Travel")

    response = await client.get(
        "/api/v1/expenses?category=Travel", headers=headers
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["category"] == "Travel"


async def test_list_search(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    await _create(client, headers, description="Late night dinner")
    await _create(client, headers, description="Taxi ride", category="Travel")

    response = await client.get("/api/v1/expenses?search=dinner", headers=headers)
    items = response.json()["items"]
    assert len(items) == 1
    assert "dinner" in items[0]["description"].lower()


async def test_list_date_range_and_amount_filters(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    await _create(client, headers, amount=10, expense_date=date(2026, 9, 1))
    await _create(client, headers, amount=500, expense_date=date(2026, 9, 10))
    await _create(client, headers, amount=5000, expense_date=date(2026, 10, 1))

    response = await client.get(
        "/api/v1/expenses?date_from=2026-09-01&date_to=2026-09-30&min_amount=100",
        headers=headers,
    )
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["amount"] == 500


async def test_list_sorting_whitelist(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    await _create(client, headers, amount=10)
    await _create(client, headers, amount=20, description="z")

    response = await client.get(
        "/api/v1/expenses?sort_by=amount&sort_order=desc", headers=headers
    )
    items = response.json()["items"]
    assert items[0]["amount"] == 20

    # SQL injection attempt through sort_by is rejected by validation.
    response = await client.get(
        "/api/v1/expenses?sort_by=amount;DROP TABLE users", headers=headers
    )
    assert response.status_code == 422


async def test_list_pagination(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    for i in range(5):
        await _create(client, headers, amount=100 + i, description=f"item{i}")

    response = await client.get(
        "/api/v1/expenses?page=2&page_size=2", headers=headers
    )
    body = response.json()
    assert body["total"] == 5
    assert body["pages"] == 3
    assert len(body["items"]) == 2


async def test_page_beyond_available_returns_empty(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    await _create(client, headers, amount=10)
    await _create(client, headers, amount=20)

    body = (await client.get("/api/v1/expenses?page=5&page_size=2", headers=headers)).json()
    assert body["items"] == []
    assert body["total"] == 2


async def test_repeated_delete_returns_404(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    created = (await _create(client, headers)).json()
    assert (await client.delete(f"/api/v1/expenses/{created['id']}", headers=headers)).status_code == 204
    assert (await client.delete(f"/api/v1/expenses/{created['id']}", headers=headers)).status_code == 404


async def test_update_rejects_invalid_category_and_method(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    created = (await _create(client, headers)).json()

    response = await client.patch(
        f"/api/v1/expenses/{created['id']}", json={"category": "Nope"}, headers=headers
    )
    assert response.status_code == 422
    response = await client.patch(
        f"/api/v1/expenses/{created['id']}", json={"payment_method": "Barter"}, headers=headers
    )
    assert response.status_code == 422


async def test_sort_by_expense_date_desc_returns_actual_order(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    await _create(client, headers, amount=1, expense_date=date(2026, 9, 3))
    await _create(client, headers, amount=2, expense_date=date(2026, 9, 1))
    await _create(client, headers, amount=3, expense_date=date(2026, 9, 2))

    items = (
        await client.get(
            "/api/v1/expenses?sort_by=expense_date&sort_order=desc", headers=headers
        )
    ).json()["items"]
    assert [i["expense_date"] for i in items] == ["2026-09-03", "2026-09-02", "2026-09-01"]


async def test_expense_persisted_in_database(client, db_session):
    """QA §5: creation writes a real database row, not just an API response."""
    from sqlalchemy import select

    from backend.app.models.expense import Expense

    data = await register_and_login(client, email="persist@example.com")
    headers = auth_header(data)
    created = (await _create(client, headers, amount=42.42)).json()

    result = await db_session.execute(
        select(Expense).where(Expense.id == created["id"])
    )
    row = result.scalar_one()
    assert float(row.amount) == 42.42
    assert str(row.user_id) == created["user_id"]
