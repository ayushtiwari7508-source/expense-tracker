"""Shared domain constants and enums."""

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import PlainSerializer

EXPENSE_CATEGORIES: tuple[str, ...] = (
    "Food",
    "Travel",
    "Shopping",
    "Education",
    "Entertainment",
    "Bills",
    "Healthcare",
    "Rent",
    "Other",
)

PAYMENT_METHODS: tuple[str, ...] = (
    "Cash",
    "UPI",
    "Credit Card",
    "Debit Card",
    "Bank Transfer",
    "Other",
)

BUDGET_STATUSES: tuple[str, ...] = ("NORMAL", "WARNING", "EXCEEDED")

SORTABLE_EXPENSE_FIELDS: dict[str, str] = {
    "expense_date": "expense_date",
    "amount": "amount",
    "category": "category",
    "payment_method": "payment_method",
    "created_at": "created_at",
    "description": "description",
}


class AlertTypeValues(StrEnum):
    WARNING = "warning"
    EXCEEDED = "exceeded"


# Decimal in Python (exact money math); serialized as a JSON number.
# Floats are used ONLY for output encoding, never for calculations.
Money = Annotated[
    Decimal,
    PlainSerializer(lambda value: float(value), return_type=float, when_used="json"),
]
