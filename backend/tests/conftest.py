"""Shared pytest fixtures.

Tests run against a dedicated PostgreSQL test database
(``expense_tracker_test``, configurable via ``TEST_DATABASE_URL``) so the
suite exercises the real schema: native UUID columns, NUMERIC money types,
CHECK constraints, and ON DELETE CASCADE behavior.

Isolation model (SQLAlchemy "joining an external transaction" recipe):
- The schema is created once per session.
- Each test gets a connection with an outer transaction; every request
  session joins that transaction in ``create_savepoint`` mode, so
  service-layer commits only release SAVEPOINTs and the outer transaction
  is rolled back after the test — leaving the database pristine.
"""

import sys
from pathlib import Path

# Make `tests` importable as a top-level package regardless of invocation dir.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collections.abc import AsyncGenerator
from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.core.config import settings
from backend.app.core.database import Base, get_db


@pytest.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Session-wide engine bound to the dedicated PostgreSQL test database."""
    engine = create_async_engine(settings.TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_connection(engine: AsyncEngine) -> AsyncGenerator[AsyncConnection, None]:
    """Per-test connection holding an outer transaction; rolled back on exit."""
    async with engine.connect() as conn:
        outer = await conn.begin()
        try:
            yield conn
        finally:
            if outer.is_active:
                await outer.rollback()


@pytest.fixture
def session_factory(
    db_connection: AsyncConnection,
) -> async_sessionmaker[AsyncSession]:
    """Factory for sessions joined to the current test's outer transaction.

    ``join_transaction_mode="create_savepoint"`` means service-layer
    ``commit()`` calls only release a SAVEPOINT — the outer transaction
    (and all test data) is discarded on teardown.
    """

    def factory() -> AsyncSession:
        return AsyncSession(
            bind=db_connection,
            expire_on_commit=False,
            autoflush=False,
            join_transaction_mode="create_savepoint",
        )

    return factory


@pytest.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """A plain session for direct database assertions inside a test."""
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture
def app(session_factory: async_sessionmaker[AsyncSession]) -> FastAPI:
    """The FastAPI app with get_db overridden to use the test transaction."""
    from backend.app.main import create_app

    application = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        session = session_factory()
        try:
            yield session
        finally:
            await session.close()

    application.dependency_overrides[get_db] = override_get_db
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ------------------------------------------------------------- API helpers


def get_cookie_token(client: AsyncClient) -> str | None:
    """Auth token from the client's cookie jar (HttpOnly cookie auth)."""
    return client.cookies.get(settings.JWT_COOKIE_NAME)


def auth_header(token_response: dict) -> dict:
    """Bearer header built from an auth dict (still accepted by the API)."""
    return {"Authorization": f"Bearer {token_response['access_token']}"}


async def register_and_login(
    client: AsyncClient,
    email: str = "ayush@example.com",
    password: str = "StrongPassword123",
    name: str = "Ayush",
) -> dict:
    """Register and log in a user.

    Login now sets the JWT as an HttpOnly cookie (stored automatically in
    the httpx cookie jar); the response body no longer contains the token.
    The token is extracted from the jar and included in the returned dict so
    ``auth_header(...)`` keeps working for tests that exercise the bearer
    fallback directly.
    """
    await client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, f"login failed for {email}: {response.text}"
    token = get_cookie_token(client)
    assert token, "login did not set the auth cookie"
    return {"detail": response.json().get("detail"), "access_token": token}


# ---------------------------------------------------------- data factories


def make_expense_payload(
    amount: str | float = "250.50",
    category: str = "Food",
    description: str | None = "Dinner",
    payment_method: str = "UPI",
    expense_date: date | None = None,
) -> dict:
    return {
        "amount": float(amount),
        "category": category,
        "description": description,
        "payment_method": payment_method,
        "expense_date": (expense_date or date(2026, 9, 16)).isoformat(),
    }


def make_budget_payload(
    amount: float = 5000,
    category: str | None = "Food",
    start: date | None = None,
    end: date | None = None,
    threshold: float = 80,
) -> dict:
    return {
        "category": category,
        "amount": amount,
        "start_date": (start or date(2026, 9, 1)).isoformat(),
        "end_date": (end or date(2026, 9, 30)).isoformat(),
        "alert_threshold": threshold,
    }


__all__ = [
    "register_and_login",
    "auth_header",
    "make_expense_payload",
    "make_budget_payload",
    "Decimal",
]
