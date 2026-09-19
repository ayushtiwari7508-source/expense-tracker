"""User profile routes."""

from fastapi import APIRouter, status

from backend.app.api.deps import CurrentUser, DbSession
from backend.app.schemas.auth import MessageResponse
from backend.app.schemas.user import PasswordChange, UserResponse, UserUpdate
from backend.app.services import auth_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Current user profile",
)
async def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_me(
    payload: UserUpdate, current_user: CurrentUser, db: DbSession
) -> UserResponse:
    user = await auth_service.update_profile(db, current_user, payload)
    return UserResponse.model_validate(user)


@router.patch(
    "/me/password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change password",
    description="Verifies the current password, then stores a new Argon2 hash.",
)
async def change_password(
    payload: PasswordChange, current_user: CurrentUser, db: DbSession
) -> MessageResponse:
    await auth_service.change_password(db, current_user, payload)
    return MessageResponse(detail="Password updated")
