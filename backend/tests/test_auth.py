"""Authentication endpoint tests (HttpOnly cookie auth)."""

from unittest.mock import patch

import jwt as pyjwt
from httpx import AsyncClient

from backend.app.core.config import settings
from backend.app.core.security import create_access_token, decode_access_token
from backend.app.models.user import User
from tests.conftest import auth_header, register_and_login


async def _register(client: AsyncClient, email: str, password: str = "StrongPassword123") -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"name": "Ayush", "email": email, "password": password},
    )


async def _login(client: AsyncClient, email: str, password: str = "StrongPassword123"):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


# ------------------------------------------------------------------ register


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
    await _register(client, "dup@example.com")
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


# --------------------------------------------------------------------- login


async def test_login_sets_httponly_cookie(client):
    """Login sets the JWT in an HttpOnly cookie and the body has no token."""
    await _register(client, "cookie@example.com")
    response = await _login(client, "cookie@example.com")
    assert response.status_code == 200

    set_cookie = response.headers.get("set-cookie", "")
    assert f"{settings.JWT_COOKIE_NAME}=" in set_cookie
    assert "httponly" in set_cookie.lower()
    assert "path=/" in set_cookie.lower()

    # The raw JWT must not be exposed to JavaScript.
    assert "access_token" not in response.json()
    assert settings.JWT_COOKIE_NAME not in (response.text or "")


async def test_login_cookie_secure_flag_in_production(client):
    """In production the cookie must carry Secure and HttpOnly."""
    await _register(client, "prodcookie@example.com")
    with patch.object(settings, "APP_ENV", "production"):
        response = await _login(client, "prodcookie@example.com")
    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert "secure" in set_cookie.lower()
    assert "httponly" in set_cookie.lower()
    assert "samesite=lax" in set_cookie.lower()


async def test_login_wrong_password(client):
    await _register(client, "wrongpw@example.com")
    response = await _login(client, "wrongpw@example.com", "WrongPassword123")
    assert response.status_code == 401


async def test_login_unknown_user(client):
    response = await _login(client, "ghost@example.com")
    assert response.status_code == 401


async def test_login_oauth2_form(client):
    await _register(client, "form@example.com")
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "form@example.com", "password": "StrongPassword123"},
    )
    assert response.status_code == 200
    assert client.cookies.get(settings.JWT_COOKIE_NAME)


async def test_jwt_cookie_contains_user_id(client):
    await register_and_login(client, email="jwtc@example.com")
    payload = decode_access_token(client.cookies.get(settings.JWT_COOKIE_NAME))
    assert payload["sub"]
    assert payload["type"] == "access"


# --------------------------------------------------------------- /auth/me


async def test_me_requires_auth(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_with_cookie(client):
    await register_and_login(client, email="me@example.com")
    response = await client.get("/api/v1/auth/me")  # cookie sent automatically
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


async def test_me_with_bearer_fallback(client):
    data = await register_and_login(client, email="bearer@example.com")
    response = await client.get("/api/v1/auth/me", headers=auth_header(data))
    assert response.status_code == 200
    assert response.json()["email"] == "bearer@example.com"


async def test_me_invalid_cookie_rejected(client):
    client.cookies.set(settings.JWT_COOKIE_NAME, "not-a-token")
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_expired_cookie_rejected(client):
    with patch.object(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", -1):
        token = create_access_token(subject="00000000-0000-0000-0000-000000000000")
    client.cookies.set(settings.JWT_COOKIE_NAME, token)
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_tampered_cookie_rejected(client):
    token = create_access_token(subject="00000000-0000-0000-0000-000000000000")
    client.cookies.set(settings.JWT_COOKIE_NAME, token[:-3] + "abc")  # break signature
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_wrong_secret_cookie_rejected(client):
    token = pyjwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000000", "type": "access", "exp": 4102444800},
        "a-completely-different-secret",
        algorithm=settings.JWT_ALGORITHM,
    )
    client.cookies.set(settings.JWT_COOKIE_NAME, token)
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_cookie_with_unknown_user_rejected(client):
    token = create_access_token(subject="00000000-0000-0000-0000-000000000000")
    client.cookies.set(settings.JWT_COOKIE_NAME, token)
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


# ------------------------------------------------------------------ logout


async def test_logout_clears_cookie(client):
    await register_and_login(client, email="logout@example.com")
    assert client.cookies.get(settings.JWT_COOKIE_NAME)

    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200

    # The server invalidated the cookie: expiry in the past / empty value.
    set_cookie = response.headers.get("set-cookie", "").lower()
    assert "expires=thu, 01 jan 1970" in set_cookie or "max-age=0" in set_cookie
    assert f'{settings.JWT_COOKIE_NAME}=""' in set_cookie

    # A subsequent /auth/me must fail (client honors the cleared cookie).
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_logout_without_session_succeeds(client):
    """Logout is idempotent: no valid session required."""
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200


# ------------------------------------------------------ password handling


async def test_password_stored_hashed_in_database(client, db_session):
    """QA §8: the stored credential is an Argon2id hash, never plaintext."""
    from sqlalchemy import select

    await _register(client, "hashcheck@example.com")
    result = await db_session.execute(select(User).where(User.email == "hashcheck@example.com"))
    user = result.scalar_one()
    assert user.password_hash.startswith("$argon2id$"), "password not Argon2id-hashed"
    assert "StrongPassword123" not in user.password_hash


async def test_password_change_flow(client):
    await _register(client, "pwchange@example.com")
    data = await register_and_login(client, email="pwchange@example.com")
    headers = auth_header(data)
    response = await client.patch(
        "/api/v1/users/me/password",
        headers=headers,
        json={"current_password": "StrongPassword123", "new_password": "NewStrong123"},
    )
    assert response.status_code == 200

    # Old password no longer works.
    response = await _login(client, "pwchange@example.com", "StrongPassword123")
    assert response.status_code == 401

    # New password works (and sets a fresh cookie).
    response = await _login(client, "pwchange@example.com", "NewStrong123")
    assert response.status_code == 200
    assert client.cookies.get(settings.JWT_COOKIE_NAME)


async def test_password_change_requires_correct_current(client):
    data = await register_and_login(client, email="pwbad@example.com")
    response = await client.patch(
        "/api/v1/users/me/password",
        headers=auth_header(data),
        json={"current_password": "WrongPassword123", "new_password": "NewStrong123"},
    )
    assert response.status_code == 401
