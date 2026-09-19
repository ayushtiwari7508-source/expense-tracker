"""Shared FastAPI dependencies."""

import uuid
from typing import Annotated

import jwt as pyjwt
from fastapi import Depends, Request
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.exceptions import AuthenticationError
from backend.app.core.security import decode_access_token
from backend.app.models.user import User

DbSession = Annotated[AsyncSession, Depends(get_db)]


def _extract_token(request: Request) -> str | None:
    """Auth token for the request.

    An explicit ``Authorization: Bearer`` header (deliberate non-browser API
    clients) takes precedence; otherwise the HttpOnly cookie set at login
    authenticates the browser, whose JavaScript never handles the token.
    """
    scheme, param = get_authorization_scheme_param(request.headers.get("Authorization"))
    if scheme.lower() == "bearer" and param:
        return param
    return request.cookies.get(settings.JWT_COOKIE_NAME)


async def get_current_user(
    request: Request,
    db: DbSession,
) -> User:
    """Resolve the authenticated user from the auth cookie or bearer token."""
    credentials_error = AuthenticationError("Not authenticated")
    token = _extract_token(request)
    if not token:
        raise credentials_error
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


CurrentUser = Annotated[User, Depends(get_current_user)]
