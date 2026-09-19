"""Database-level constraint tests (require real PostgreSQL).

SQLite silently ignores most CHECK constraints and uses a different
UUID/cascade model, so these tests validate the production schema where it
actually runs: native UUID columns, NUMERIC(12,2) money, CHECK constraints,
UNIQUE email, and ON DELETE CASCADE.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.alert import Alert
from backend.app.models.budget import Budget
from backend.app.models.expense import Expense
from backend.app.models.user import User
from backend.app.core.security import hash_password


async def _make_user(db: AsyncSession, email: str) -> User:
    user = User(name="DB User", email=email, password_hash=hash_password("StrongPassword123"))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def test_duplicate_email_violates_unique_constraint(db_session: AsyncSession):
    await _make_user(db_session, "unique@example.com")
    with pytest.raises(IntegrityError):
        await _make_user(db_session, "unique@example.com")
    await db_session.rollback()


async def test_expense_amount_must_be_positive(db_session: AsyncSession):
    user = await _make_user(db_session, "amount@example.com")
    expense = Expense(
        user_id=user.id,
        amount=-10,
        category="Food",
        description=None,
        payment_method="UPI",
        expense_date="2026-09-16",
    )
    db_session.add(expense)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_budget_date_range_check_constraint(db_session: AsyncSession):
    user = await _make_user(db_session, "range@example.com")
    budget = Budget(
        user_id=user.id,
        category="Food",
        amount=1000,
        start_date="2026-09-30",
        end_date="2026-09-01",  # invalid: start > end
        alert_threshold=80,
    )
    db_session.add(budget)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_budget_alert_threshold_range_check(db_session: AsyncSession):
    user = await _make_user(db_session, "thresh@example.com")
    budget = Budget(
        user_id=user.id,
        category=None,
        amount=1000,
        start_date="2026-09-01",
        end_date="2026-09-30",
        alert_threshold=150,  # invalid: > 100
    )
    db_session.add(budget)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_deleting_user_cascades_to_related_rows(db_session: AsyncSession):
    user = await _make_user(db_session, "cascade@example.com")

    expense = Expense(
        user_id=user.id,
        amount=25,
        category="Food",
        description=None,
        payment_method="UPI",
        expense_date="2026-09-16",
    )
    budget = Budget(
        user_id=user.id,
        category="Food",
        amount=100,
        start_date="2026-09-01",
        end_date="2026-09-30",
        alert_threshold=80,
    )
    db_session.add_all([expense, budget])
    await db_session.flush()
    alert = Alert(
        user_id=user.id,
        budget_id=budget.id,
        type="warning",
        message="test alert",
        is_read=False,
    )
    db_session.add(alert)
    await db_session.commit()

    await db_session.delete(user)
    await db_session.commit()

    for table, column in (("expenses", "user_id"), ("budgets", "user_id"), ("alerts", "user_id")):
        result = await db_session.execute(
            text(f"SELECT count(*) FROM {table} WHERE {column} = :uid"), {"uid": str(user.id)}
        )
        assert result.scalar_one() == 0, f"{table} rows were not cascaded away"


async def test_postgresql_native_column_types(db_session: AsyncSession):
    """Guard: the schema uses native UUID/NUMERIC/TIMESTAMPTZ columns."""
    expected = {
        ("expenses", "id"): "uuid",
        ("expenses", "amount"): "numeric",
        ("expenses", "expense_date"): "date",
        ("budgets", "alert_threshold"): "numeric",
        ("users", "created_at"): "timestamp with time zone",
    }
    for (table, column), dtype in expected.items():
        result = await db_session.execute(
            text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ),
            {"t": table, "c": column},
        )
        actual = result.scalar_one_or_none()
        assert actual == dtype, f"{table}.{column} is {actual!r}, expected {dtype!r}"


async def test_numeric_money_round_trip(db_session: AsyncSession):
    """Decimal money survives the database without float drift."""
    user = await _make_user(db_session, "decimal@example.com")
    expense = Expense(
        user_id=user.id,
        amount=250.50,  # bound as Decimal via NUMERIC(12,2)
        category="Food",
        description=None,
        payment_method="UPI",
        expense_date="2026-09-16",
    )
    db_session.add(expense)
    await db_session.commit()
    await db_session.refresh(expense)
    assert expense.amount == 250.50
