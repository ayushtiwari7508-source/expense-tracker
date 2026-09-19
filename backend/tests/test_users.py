"""User profile endpoint tests (GET/PATCH /users/me, password change)."""

from tests.conftest import auth_header, register_and_login


async def test_get_me_profile(client):
    data = await register_and_login(client, email="profile@example.com")
    response = await client.get("/api/v1/users/me", headers=auth_header(data))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "profile@example.com"
    assert body["name"] == "Ayush"
    assert "password_hash" not in body
    assert "password" not in body


async def test_update_profile_name(client):
    data = await register_and_login(client, email="upd@example.com")
    response = await client.patch(
        "/api/v1/users/me", json={"name": "Arya"}, headers=auth_header(data)
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Arya"
    # Persisted: a fresh authenticated fetch returns the new name.
    fetched = (await client.get("/api/v1/users/me", headers=auth_header(data))).json()
    assert fetched["name"] == "Arya"


async def test_update_profile_email_flow(client):
    data = await register_and_login(client, email="swap@example.com")
    headers = auth_header(data)
    response = await client.patch(
        "/api/v1/users/me", json={"email": "swapped@example.com"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["email"] == "swapped@example.com"

    # Old email can no longer log in; the new one can.
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "swap@example.com", "password": "StrongPassword123"},
    )
    assert old_login.status_code == 401
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "swapped@example.com", "password": "StrongPassword123"},
    )
    assert new_login.status_code == 200


async def test_update_profile_to_taken_email_conflicts(client):
    await register_and_login(client, email="taken@example.com")
    other = await register_and_login(client, email="free@example.com")
    response = await client.patch(
        "/api/v1/users/me", json={"email": "taken@example.com"}, headers=auth_header(other)
    )
    assert response.status_code == 409


async def test_update_profile_validation(client):
    data = await register_and_login(client, email="badname@example.com")
    # Name below min_length=2.
    response = await client.patch(
        "/api/v1/users/me", json={"name": "A"}, headers=auth_header(data)
    )
    assert response.status_code == 422
    # Malformed email.
    response = await client.patch(
        "/api/v1/users/me", json={"email": "nope"}, headers=auth_header(data)
    )
    assert response.status_code == 422


async def test_profile_requires_auth(client):
    assert (await client.get("/api/v1/users/me")).status_code == 401
    assert (await client.patch("/api/v1/users/me", json={"name": "X Y"})).status_code == 401


async def test_password_change_strength_enforced(client):
    data = await register_and_login(client, email="pwstrength@example.com")
    # No digit → violates the documented policy.
    response = await client.patch(
        "/api/v1/users/me/password",
        headers=auth_header(data),
        json={"current_password": "StrongPassword123", "new_password": "weakpassword"},
    )
    assert response.status_code == 422
    # No uppercase → also rejected.
    response = await client.patch(
        "/api/v1/users/me/password",
        headers=auth_header(data),
        json={"current_password": "StrongPassword123", "new_password": "weakpassword1"},
    )
    assert response.status_code == 422
    # Old password still works after rejected changes.
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "pwstrength@example.com", "password": "StrongPassword123"},
    )
    assert response.status_code == 200


async def test_users_me_isolated_per_user(client):
    """Profiles are per-token; user B never sees user A's data."""
    user_a = await register_and_login(client, email="me-a@example.com")
    user_b = await register_and_login(client, email="me-b@example.com")
    await client.patch("/api/v1/users/me", json={"name": "Only A"}, headers=auth_header(user_a))

    body_b = (await client.get("/api/v1/users/me", headers=auth_header(user_b))).json()
    assert body_b["name"] != "Only A"
    assert body_b["email"] == "me-b@example.com"
