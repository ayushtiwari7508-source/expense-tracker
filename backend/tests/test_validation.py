"""Malformed-request and boundary validation tests.

These probe the API contract for structured 4xx responses, no server
crashes, and no leaked internals (QA spec section 30).
"""

from tests.conftest import auth_header, make_expense_payload, register_and_login


async def _create(client, headers, payload):
    return await client.post("/api/v1/expenses", json=payload, headers=headers)


async def test_missing_json_body(client):
    data = await register_and_login(client)
    response = await client.post(
        "/api/v1/expenses",
        headers={**auth_header(data), "Content-Type": "application/json"},
    )
    assert response.status_code == 422


async def test_invalid_json_body(client):
    data = await register_and_login(client)
    response = await client.post(
        "/api/v1/expenses",
        content=b"{not json",
        headers={**auth_header(data), "Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert "Traceback" not in response.text


async def test_wrong_data_types(client):
    data = await register_and_login(client)
    payload = make_expense_payload()
    payload["amount"] = "not-a-number"  # raw, bypassing the factory coercion
    response = await _create(client, auth_header(data), payload)
    assert response.status_code == 422


async def test_null_required_fields(client):
    data = await register_and_login(client)
    response = await _create(
        client,
        auth_header(data),
        {"amount": None, "category": "Food", "payment_method": "UPI", "expense_date": "2026-09-16"},
    )
    assert response.status_code == 422


async def test_missing_required_fields(client):
    data = await register_and_login(client)
    cases = (
        {"category": "Food", "payment_method": "UPI", "expense_date": "2026-09-16"},
        {"amount": 10, "payment_method": "UPI", "expense_date": "2026-09-16"},
        {"amount": 10, "category": "Food", "expense_date": "2026-09-16"},
        {"amount": 10, "category": "Food", "payment_method": "UPI"},
    )
    for payload in cases:
        response = await _create(client, auth_header(data), payload)
        assert response.status_code == 422, payload


async def test_invalid_date_format(client):
    data = await register_and_login(client)
    payload = make_expense_payload()
    payload["expense_date"] = "16-09-2026"  # raw, bypassing the factory coercion
    response = await _create(client, auth_header(data), payload)
    assert response.status_code == 422


async def test_oversized_description(client):
    data = await register_and_login(client)
    response = await _create(
        client, auth_header(data), make_expense_payload(description="x" * 256)
    )
    assert response.status_code == 422


async def test_amount_boundaries(client):
    """Minimum valid amount is 0.01; zero/negative/>2dp are rejected."""
    data = await register_and_login(client)
    headers = auth_header(data)

    ok = await _create(client, headers, make_expense_payload(amount=0.01))
    assert ok.status_code == 201

    for bad in (0, -0.01, -100):
        response = await _create(client, headers, make_expense_payload(amount=bad))
        assert response.status_code == 422, bad

    response = await _create(client, headers, make_expense_payload(amount=10.999))
    assert response.status_code == 422


async def test_invalid_uuid_path_param(client):
    data = await register_and_login(client)
    response = await client.get("/api/v1/expenses/not-a-uuid", headers=auth_header(data))
    assert response.status_code == 422


async def test_pagination_bounds(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    assert (await client.get("/api/v1/expenses?page=0", headers=headers)).status_code == 422
    assert (await client.get("/api/v1/expenses?page_size=0", headers=headers)).status_code == 422
    assert (await client.get("/api/v1/expenses?page_size=101", headers=headers)).status_code == 422
    # Upper bound of page_size is accepted.
    assert (await client.get("/api/v1/expenses?page_size=100", headers=headers)).status_code == 200


async def test_negative_amount_filters_rejected(client):
    data = await register_and_login(client)
    headers = auth_header(data)
    assert (await client.get("/api/v1/expenses?min_amount=-1", headers=headers)).status_code == 422
    assert (await client.get("/api/v1/expenses?max_amount=-1", headers=headers)).status_code == 422


async def test_unknown_filter_category_rejected(client):
    data = await register_and_login(client)
    response = await client.get(
        "/api/v1/expenses?category=NotACategory", headers=auth_header(data)
    )
    assert response.status_code == 422


async def test_validation_errors_are_structured(client):
    """422 bodies use the app's structured error envelope:
    {"detail": "Invalid request data", "errors": [{loc, msg, type}, ...]}
    — never a traceback or internal details."""
    data = await register_and_login(client)
    response = await _create(client, auth_header(data), make_expense_payload(category="Nope"))
    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Invalid request data"
    assert isinstance(body["errors"], list)
    assert len(body["errors"]) >= 1
    assert all({"loc", "msg", "type"} <= set(err) for err in body["errors"])
    assert "Traceback" not in response.text
