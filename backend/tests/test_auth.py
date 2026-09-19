"""Authentication endpoint tests."""

from unittest.mock import patch

from backend.app.core.security import decode_access_token
from backend.app.models.user import User
from tests.conftest import auth_header, register_and_login


async def test_register_success(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"name": "Ayush", "email": "ayush@example.com", "password": "StrongPassword123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ayush"
    assert body["email"] == "ayush@example.com"
    assert "password_hash" not in body
    assert "password" not in body


async def test_register_duplicate_email(client):
    await client.post(
        "/api/v1/auth/register",
        json={"name": "Ayush", "email": "dup@example.com", "password": "StrongPassword123"},
    )
    response = await client.post(
        "/api/v1/auth/register",
        json={"name": "Other", "email": "DUP@example.com", "password": "StrongPassword123"},
    )
    assert response.status_code == 409


async def test_register_invalid_password(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"name": "Ayush", "email": "shortpw@example.com", "password": "short"},
    )
    assert response.status_code == 422


async def test_register_invalid_email(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"name": "Ayush", "email": "not-an-email", "password": "StrongPassword123"},
    )
    assert response.status_code == 422


async def test_register_email_normalized(client, db_session):
    await client.post(
        "/api/v1/auth/register",
        json={"name": "Ayush", "email": "  Mixed@Example.COM ", "password": "StrongPassword123"},
    )
    from sqlalchemy import select

    result = await db_session.execute(select(User).where(User.email == "mixed@example.com"))
    assert result.scalar_one_or_none() is not None


async def test_login_success(client):
    data = await register_and_login(client)
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client):
    await client.post(
        "/api/v1/auth/register",
        json={"name": "Ayush", "email": "wrongpw@example.com", "password": "StrongPassword123"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@example.com", "password": "WrongPassword123"},
    )
    assert response.status_code == 401


async def test_login_unknown_user(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "StrongPassword123"},
    )
    assert response.status_code == 401


async def test_login_oauth2_form(client):
    await client.post(
        "/api/v1/auth/register",
        json={"name": "Ayush", "email": "form@example.com", "password": "StrongPassword123"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "form@example.com", "password": "StrongPassword123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_jwt_contains_user_id(client):
    data = await register_and_login(client, email="jwt@example.com")
    payload = decode_access_token(data["access_token"])
    assert payload["sub"]
    assert payload["type"] == "access"


async def test_me_requires_token(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_with_token(client):
    data = await register_and_login(client, email="me@example.com")
    response = await client.get("/api/v1/auth/me", headers=auth_header(data))
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


async def test_me_invalid_token(client):
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-token"}
    )
    assert response.status_code == 401


async def test_me_expired_token(client, app):
    from backend.app.core import security

    with patch.object(security.settings, "ACCESS_TOKEN_EXPIRE_MINUTES", -1):
        token = security.create_access_token(subject="00000000-0000-0000-0000-000000000000")
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


async def test_password_stored_hashed_in_database(client, db_session):
    """QA §8: the stored credential is an Argon2id hash, never plaintext."""
    from sqlalchemy import select

    await client.post(
        "/api/v1/auth/register",
        json={"name": "Ayush", "email": "hashcheck@example.com", "password": "StrongPassword123"},
    )
    result = await db_session.execute(select(User).where(User.email == "hashcheck@example.com"))
    user = result.scalar_one()
    assert user.password_hash.startswith("$argon2id$"), "password not Argon2id-hashed"
    assert "StrongPassword123" not in user.password_hash


async def test_password_change_flow(client):
    data = await register_and_login(client, email="pwchange@example.com")
    headers = auth_header(data)
    response = await client.patch(
        "/api/v1/users/me/password",
        headers=headers,
        json={"current_password": "StrongPassword123", "new_password": "NewStrong123"},
    )
    assert response.status_code == 200

    # Old password no longer works.
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "pwchange@example.com", "password": "StrongPassword123"},
    )
    assert response.status_code == 401

    # New password works.
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "pwchange@example.com", "password": "NewStrong123"},
    )
    assert response.status_code == 200


async def test_password_change_requires_correct_current(client):
    data = await register_and_login(client, email="pwbad@example.com")
    response = await client.patch(
        "/api/v1/users/me/password",
        headers=auth_header(data),
        json={"current_password": "WrongPassword123", "new_password": "NewStrong123"},
    )
    assert response.status_code == 401
