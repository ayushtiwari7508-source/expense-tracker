"""Health and readiness endpoints."""

from fastapi import APIRouter
from sqlalchemy import text

from backend.app.core.database import get_session_factory

router = APIRouter(tags=["Health"])


@router.get(
    "",
    summary="Service health",
    description="Returns basic service health information.",
)
async def health() -> dict:
    return {"status": "healthy", "service": "expense-tracker-api"}


@router.get(
    "/db",
    summary="Database readiness",
    description="Verifies the PostgreSQL connection with a live query.",
)
async def health_db() -> dict:
    factory = get_session_factory()
    try:
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return {"status": "unhealthy", "database": "unavailable"}
