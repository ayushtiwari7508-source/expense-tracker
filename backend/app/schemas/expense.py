"""Expense schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.schemas.common import (
    EXPENSE_CATEGORIES,
    PAYMENT_METHODS,
    SORTABLE_EXPENSE_FIELDS,
    Money,
)


class ExpenseBase(BaseModel):
    amount: Money = Field(..., gt=0, max_digits=12, decimal_places=2)
    category: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(None, max_length=255)
    payment_method: str = Field(..., min_length=1, max_length=30)
    expense_date: date

    @field_validator("category")
    @classmethod
    def category_allowed(cls, value: str) -> str:
        if value not in EXPENSE_CATEGORIES:
            raise ValueError(f"category must be one of {list(EXPENSE_CATEGORIES)}")
        return value

    @field_validator("payment_method")
    @classmethod
    def payment_method_allowed(cls, value: str) -> str:
        if value not in PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of {list(PAYMENT_METHODS)}")
        return value


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    amount: Money | None = Field(None, gt=0, max_digits=12, decimal_places=2)
    category: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = Field(None, max_length=255)
    payment_method: str | None = Field(None, min_length=1, max_length=30)
    expense_date: date | None = None

    @field_validator("category")
    @classmethod
    def category_allowed(cls, value: str | None) -> str | None:
        if value is not None and value not in EXPENSE_CATEGORIES:
            raise ValueError(f"category must be one of {list(EXPENSE_CATEGORIES)}")
        return value

    @field_validator("payment_method")
    @classmethod
    def payment_method_allowed(cls, value: str | None) -> str | None:
        if value is not None and value not in PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of {list(PAYMENT_METHODS)}")
        return value


class ExpenseResponse(ExpenseBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime


class ExpenseListParams(BaseModel):
    """Query parameters for listing expenses."""

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    search: str | None = Field(None, max_length=100)
    category: str | None = None
    payment_method: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    min_amount: Decimal | None = Field(None, ge=0)
    max_amount: Decimal | None = Field(None, ge=0)
    sort_by: str = Field("expense_date")
    sort_order: str = Field("desc", pattern="^(asc|desc)$")

    @field_validator("category")
    @classmethod
    def category_allowed(cls, value: str | None) -> str | None:
        if value is not None and value not in EXPENSE_CATEGORIES:
            raise ValueError(f"category must be one of {list(EXPENSE_CATEGORIES)}")
        return value

    @field_validator("payment_method")
    @classmethod
    def payment_method_allowed(cls, value: str | None) -> str | None:
        if value is not None and value not in PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of {list(PAYMENT_METHODS)}")
        return value

    @field_validator("sort_by")
    @classmethod
    def sort_by_whitelisted(cls, value: str) -> str:
        if value not in SORTABLE_EXPENSE_FIELDS:
            raise ValueError(
                f"sort_by must be one of {sorted(SORTABLE_EXPENSE_FIELDS.keys())}"
            )
        return value
