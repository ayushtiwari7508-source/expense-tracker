"""Shared FastAPI dependencies."""

import uuid
from typing import Annotated

import jwt as pyjwt
from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.exceptions import AuthenticationError
from backend.app.core.security import decode_access_token
from backend.app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    """Resolve the authenticated user from the bearer token."""
    credentials_error = AuthenticationError("Not authenticated")
    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_error
        user_uuid = uuid.UUID(user_id)  # reject malformed subjects
    except pyjwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token has expired") from exc
    except pyjwt.InvalidTokenError as exc:
        raise credentials_error from exc
    except ValueError as exc:
        raise credentials_error from exc

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
