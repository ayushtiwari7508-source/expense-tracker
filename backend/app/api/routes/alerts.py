"""Alert routes."""

from uuid import UUID

from fastapi import APIRouter, status

from backend.app.api.deps import CurrentUser, DbSession
from backend.app.schemas.alert import AlertListResponse, AlertResponse
from backend.app.schemas.auth import MessageResponse
from backend.app.services import alert_service

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get(
    "",
    response_model=AlertListResponse,
    summary="List alerts",
    description="Returns the authenticated user's alerts with an unread count.",
)
async def list_alerts(
    current_user: CurrentUser,
    db: DbSession,
    unread_only: bool = False,
) -> AlertListResponse:
    items, unread_count = await alert_service.list_alerts(
        db, current_user.id, unread_only=unread_only
    )
    return AlertListResponse(
        items=[AlertResponse.model_validate(a) for a in items],
        unread_count=unread_count,
    )


@router.patch(
    "/{alert_id}/read",
    response_model=AlertResponse,
    summary="Mark an alert as read",
)
async def mark_read(alert_id: UUID, current_user: CurrentUser, db: DbSession):
    alert = await alert_service.mark_alert_read(db, current_user.id, alert_id)
    return AlertResponse.model_validate(alert)


@router.patch(
    "/read-all",
    response_model=MessageResponse,
    summary="Mark all alerts as read",
)
async def mark_all_read(current_user: CurrentUser, db: DbSession):
    updated = await alert_service.mark_all_alerts_read(db, current_user.id)
    return MessageResponse(detail=f"Marked {updated} alert(s) as read")
