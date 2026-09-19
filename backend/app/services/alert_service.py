"""Alert business logic, including automatic budget alert generation."""

import logging
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundError
from backend.app.models.alert import Alert, AlertType
from backend.app.models.budget import Budget
from backend.app.schemas.budget import BudgetUtilization

logger = logging.getLogger(__name__)


def _message_for(budget: Budget, utilization: BudgetUtilization, kind: AlertType) -> str:
    """Build a deterministic human-readable alert message."""
    scope = budget.category or "Overall"
    pct = utilization.utilization_percentage
    if kind is AlertType.EXCEEDED:
        return (
            f"{scope} budget exceeded: spent {utilization.amount_spent} of "
            f"{utilization.budget_amount} ({pct:.0f}%)."
        )
    return (
        f"{scope} budget warning: spent {utilization.amount_spent} of "
        f"{utilization.budget_amount} ({pct:.0f}%, threshold "
        f"{budget.alert_threshold:.0f}%)."
    )


async def has_alert(db: AsyncSession, budget_id: UUID, alert_type: str) -> bool:
    """Check whether an alert of this type already exists for the budget."""
    result = await db.execute(
        select(func.count()).select_from(Alert).where(
            Alert.budget_id == budget_id,
            Alert.type == alert_type,
        )
    )
    return (result.scalar_one() or 0) > 0


async def evaluate_budget_alerts(
    db: AsyncSession, user_id: UUID, budget: Budget, utilization: BudgetUtilization
) -> list[Alert]:
    """Create warning/exceeded alerts for a budget when thresholds are crossed.

    Duplicate alerts for the same budget+type are suppressed.
    """
    created: list[Alert] = []

    if utilization.utilization_percentage >= 100:
        if not await has_alert(db, budget.id, AlertType.EXCEEDED.value):
            alert = Alert(
                user_id=user_id,
                budget_id=budget.id,
                type=AlertType.EXCEEDED.value,
                message=_message_for(budget, utilization, AlertType.EXCEEDED),
            )
            db.add(alert)
            created.append(alert)
    elif utilization.utilization_percentage >= float(budget.alert_threshold):
        if not await has_alert(db, budget.id, AlertType.WARNING.value):
            alert = Alert(
                user_id=user_id,
                budget_id=budget.id,
                type=AlertType.WARNING.value,
                message=_message_for(budget, utilization, AlertType.WARNING),
            )
            db.add(alert)
            created.append(alert)

    if created:
        await db.commit()
        for alert in created:
            await db.refresh(alert)
        logger.info("Created %d alert(s) for budget %s", len(created), budget.id)
    return created


async def get_alert_owned(db: AsyncSession, user_id: UUID, alert_id: UUID) -> Alert:
    """Fetch an alert enforcing ownership."""
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id)
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise NotFoundError("Alert not found")
    return alert


async def list_alerts(
    db: AsyncSession,
    user_id: UUID,
    unread_only: bool = False,
) -> tuple[list[Alert], int]:
    """List the user's alerts (optionally unread only) plus an unread count."""
    query = select(Alert).where(Alert.user_id == user_id)
    if unread_only:
        query = query.where(Alert.is_read.is_(False))
    query = query.order_by(Alert.created_at.desc())
    items = list((await db.execute(query)).scalars().all())

    unread_count = (
        await db.execute(
            select(func.count()).select_from(Alert).where(
                Alert.user_id == user_id, Alert.is_read.is_(False)
            )
        )
    ).scalar_one()
    return items, unread_count


async def mark_alert_read(db: AsyncSession, user_id: UUID, alert_id: UUID) -> Alert:
    """Mark a single owned alert as read."""
    alert = await get_alert_owned(db, user_id, alert_id)
    alert.is_read = True
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def mark_all_alerts_read(db: AsyncSession, user_id: UUID) -> int:
    """Mark every unread alert for the user as read; return the count updated."""
    result = await db.execute(
        Alert.__table__.update()
        .where(Alert.user_id == user_id, Alert.is_read.is_(False))
        .values(is_read=True)
    )
    await db.commit()
    return result.rowcount or 0
