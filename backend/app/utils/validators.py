"""Reusable validation helpers."""

import re

from backend.app.core.exceptions import ValidationError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_name(name: str) -> str:
    """Validate a person's name: trimmed, 2-100 chars, letters/spaces allowed."""
    name = name.strip()
    if len(name) < 2 or len(name) > 100:
        raise ValidationError("Name must be between 2 and 100 characters")
    return name


def normalize_email(email: str) -> str:
    """Lowercase and trim an email address."""
    return email.strip().lower()


def validate_email(email: str) -> str:
    """Validate email format after normalization."""
    email = normalize_email(email)
    if not EMAIL_RE.match(email):
        raise ValidationError("Invalid email address")
    return email
