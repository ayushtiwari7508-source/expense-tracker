"""Authentication schemas."""

from pydantic import BaseModel, EmailStr, Field, field_validator

from backend.app.schemas.user import validate_password_strength


class RegisterRequest(BaseModel):
    """Registration payload (same shape as UserCreate)."""

    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class LoginRequest(BaseModel):
    """JSON login payload."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    detail: str
