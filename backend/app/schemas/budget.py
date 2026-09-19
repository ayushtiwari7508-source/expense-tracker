"""Budget schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.schemas.common import EXPENSE_CATEGORIES, Money


class BudgetBase(BaseModel):
    category: str | None = Field(None, max_length=50)
    amount: Money = Field(..., gt=0, max_digits=12, decimal_places=2)
    start_date: date
    end_date: date
    alert_threshold: Money = Field(..., ge=0, le=100, max_digits=5, decimal_places=2)

    @field_validator("category")
    @classmethod
    def category_allowed(cls, value: str | None) -> str | None:
        if value is not None and value not in EXPENSE_CATEGORIES:
            raise ValueError(f"category must be one of {list(EXPENSE_CATEGORIES)} or null")
        return value

    @model_validator(mode="after")
    def validate_date_range(self) -> "BudgetBase":
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    category: str | None = Field(None, max_length=50)
    amount: Money | None = Field(None, gt=0, max_digits=12, decimal_places=2)
    start_date: date | None = None
    end_date: date | None = None
    alert_threshold: Money | None = Field(None, ge=0, le=100, max_digits=5, decimal_places=2)

    @field_validator("category")
    @classmethod
    def category_allowed(cls, value: str | None) -> str | None:
        if value is not None and value not in EXPENSE_CATEGORIES:
            raise ValueError(f"category must be one of {list(EXPENSE_CATEGORIES)} or null")
        return value


class BudgetUtilization(BaseModel):
    budget_amount: Money
    amount_spent: Money
    remaining_amount: Money
    utilization_percentage: float
    status: str


class BudgetResponse(BudgetBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime


class BudgetWithUtilization(BudgetResponse):
    utilization: BudgetUtilization
