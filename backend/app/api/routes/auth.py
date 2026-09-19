"""Authentication routes.

Authentication uses an HttpOnly cookie: login sets the JWT in a secure cookie
(see ``app/core/cookies.py``); the browser sends it automatically and frontend
JavaScript never handles the token. The Authorization bearer header remains
accepted by the auth dependency as a fallback for non-browser API clients.
"""

from fastapi import APIRouter, Request, Response, status

from backend.app.api.deps import CurrentUser, DbSession
from backend.app.core.cookies import clear_auth_cookie, set_auth_cookie
from backend.app.core.exceptions import ValidationError
from backend.app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
)
from backend.app.schemas.user import UserResponse
from backend.app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a user with a securely hashed (Argon2) password.",
)
async def register(payload: RegisterRequest, db: DbSession) -> UserResponse:
    user = await auth_service.register_user(db, payload)
    return UserResponse.model_validate(user)


async def _extract_credentials(request: Request) -> tuple[str, str]:
    """Extract email/password from an OAuth2 form or a JSON body."""
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/x-www-form-urlencoded") or content_type.startswith(
        "multipart/form-data"
    ):
        form = await request.form()
        email = form.get("username") or form.get("email")
        password = form.get("password")
    else:
        try:
            body = await request.json()
        except Exception:
            body = None
        if not isinstance(body, dict):
            raise ValidationError("email and password are required")
        email = body.get("email")
        password = body.get("password")

    if not email or not password:
        raise ValidationError("email and password are required")
    return str(email), str(password)


@router.post(
    "/login",
    response_model=UserResponse,
    summary="Login and set the auth cookie",
    description=(
        "Validates credentials and sets the JWT access token in an HttpOnly "
        "cookie (browser sends it automatically). The response body returns "
        "only the user profile — the raw token is never exposed to JavaScript."
    ),
)
async def login(request: Request, response: Response, db: DbSession) -> UserResponse:
    email, password = await _extract_credentials(request)
    user = await auth_service.authenticate_user(db, email, password)
    set_auth_cookie(response, auth_service.create_token_for_user(user))
    return UserResponse.model_validate(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Current user profile",
    description="Returns the authenticated user's profile from the JWT.",
)
async def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout and clear the auth cookie",
    description=(
        "Removes the authentication cookie using the same name/path/domain "
        "it was set with. Intentionally requires no valid session so an "
        "expired-cookie logout still succeeds."
    ),
)
async def logout(response: Response) -> MessageResponse:
    clear_auth_cookie(response)
    return MessageResponse(detail="Logged out")
