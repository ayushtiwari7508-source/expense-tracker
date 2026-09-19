"""Budget ORM model."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class Budget(Base):
    """A spending budget, either overall (category NULL) or per-category."""

    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_budgets_amount_positive"),
        CheckConstraint("start_date <= end_date", name="ck_budgets_date_range"),
        CheckConstraint(
            "alert_threshold >= 0 AND alert_threshold <= 100",
            name="ck_budgets_alert_threshold_range",
        ),
        Index("ix_budgets_user_dates", "user_id", "start_date", "end_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    alert_threshold: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="budgets")  # noqa: F821
    alerts: Mapped[list["Alert"]] = relationship(  # noqa: F821
        back_populates="budget", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Budget id={self.id} category={self.category!r} amount={self.amount}>"
