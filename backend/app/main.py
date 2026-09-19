"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.database import dispose_engine
from backend.app.core.exceptions import register_exception_handlers
from backend.app.core.logging import configure_logging
from backend.app.api.routes import (
    alerts,
    analytics,
    auth,
    budgets,
    expenses,
    health,
    users,
)

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Dispose the DB engine pool on shutdown."""
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description=(
            "Expense Tracker with Analytics backend: expenses, budgets, "
            "alerts, and a factual analytics engine."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    api_prefix = settings.API_V1_PREFIX
    app.include_router(health.router, prefix=f"{api_prefix}/health")
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(expenses.router, prefix=api_prefix)
    app.include_router(budgets.router, prefix=api_prefix)
    app.include_router(alerts.router, prefix=api_prefix)
    app.include_router(analytics.router, prefix=api_prefix)

    return app


app = create_app()
