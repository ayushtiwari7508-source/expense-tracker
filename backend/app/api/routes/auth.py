"""Authentication routes."""

from fastapi import APIRouter, Request, status

from backend.app.api.deps import CurrentUser, DbSession
from backend.app.core.exceptions import ValidationError
from backend.app.schemas.auth import (
    MessageResponse,
    RegisterRequest,
    TokenResponse,
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
    response_model=TokenResponse,
    summary="Login (OAuth2 password flow)",
    description=(
        "Accepts OAuth2 form credentials (username=email, password) and also "
        "accepts a JSON body with email/password for convenience. Returns a "
        "JWT bearer access token."
    ),
)
async def login(request: Request, db: DbSession) -> TokenResponse:
    email, password = await _extract_credentials(request)
    user = await auth_service.authenticate_user(db, email, password)
    return TokenResponse(access_token=auth_service.create_token_for_user(user))


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
    summary="Logout (client-side token discard)",
)
async def logout(current_user: CurrentUser) -> MessageResponse:
    _ = current_user  # stateless JWT: client discards the token
    return MessageResponse(detail="Logged out")
