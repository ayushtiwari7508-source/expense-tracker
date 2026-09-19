"""Authentication and user profile business logic."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import AuthenticationError, ConflictError
from backend.app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from backend.app.models.user import User
from backend.app.schemas.auth import RegisterRequest
from backend.app.schemas.user import PasswordChange, UserUpdate


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Fetch a user by normalized email."""
    result = await db.execute(
        select(User).where(User.email == _normalize_email(email))
    )
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, payload: RegisterRequest) -> User:
    """Create a new user with a hashed password."""
    email = _normalize_email(payload.email)
    existing = await get_user_by_email(db, email)
    if existing is not None:
        raise ConflictError("Email already registered")

    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """Validate credentials and return the user, or raise AuthenticationError."""
    user = await get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise AuthenticationError("Incorrect email or password")
    return user


def create_token_for_user(user: User) -> str:
    """Create a JWT access token for the given user."""
    return create_access_token(subject=str(user.id))


async def update_profile(db: AsyncSession, user: User, payload: UserUpdate) -> User:
    """Update the authenticated user's profile fields."""
    if payload.email is not None:
        new_email = _normalize_email(payload.email)
        if new_email != user.email:
            existing = await get_user_by_email(db, new_email)
            if existing is not None:
                raise ConflictError("Email already registered")
            user.email = new_email
    if payload.name is not None:
        user.name = payload.name.strip()
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def change_password(
    db: AsyncSession, user: User, payload: PasswordChange
) -> None:
    """Change the user's password after verifying the current one."""
    if not verify_password(payload.current_password, user.password_hash):
        raise AuthenticationError("Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    db.add(user)
    await db.commit()
