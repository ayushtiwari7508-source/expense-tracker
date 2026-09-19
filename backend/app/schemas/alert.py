"""Alert schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    budget_id: UUID
    type: str
    message: str
    is_read: bool
    created_at: datetime


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    unread_count: int
