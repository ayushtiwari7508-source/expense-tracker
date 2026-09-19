"""Alert ORM model."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class AlertType(StrEnum):
    """Kinds of budget alerts."""

    WARNING = "warning"
    EXCEEDED = "exceeded"


class Alert(Base):
    """A budget alert generated for a user."""

    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_user_created", "user_id", "created_at"),
        Index("ix_alerts_budget", "budget_id"),
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
    budget_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("budgets.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="alerts")  # noqa: F821
    budget: Mapped["Budget"] = relationship("Budget", back_populates="alerts")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Alert id={self.id} type={self.type!r} is_read={self.is_read}>"
