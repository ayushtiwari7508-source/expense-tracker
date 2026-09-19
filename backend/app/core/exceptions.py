"""Application exceptions and FastAPI exception handlers."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception."""

    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(detail, status.HTTP_404_NOT_FOUND)


class ConflictError(AppException):
    """Resource conflict (e.g. duplicate email)."""

    def __init__(self, detail: str = "Resource conflict") -> None:
        super().__init__(detail, status.HTTP_409_CONFLICT)


class AuthenticationError(AppException):
    """Authentication failure."""

    def __init__(self, detail: str = "Not authenticated") -> None:
        super().__init__(detail, status.HTTP_401_UNAUTHORIZED)


class ValidationError(AppException):
    """Domain-level validation failure."""

    def __init__(self, detail: str = "Invalid request data") -> None:
        # HTTP_422_UNPROCESSABLE_CONTENT is the newer name; fall back for older Starlette.
        code_422 = (
            status.HTTP_422_UNPROCESSABLE_CONTENT
            if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT")
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        super().__init__(detail, code_422)


def _error_response(detail: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


def register_exception_handlers(app: FastAPI) -> None:
    """Attach consistent error handlers to the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
        return _error_response(exc.detail, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Only include JSON-safe primitives from the error contexts.
        safe_errors = []
        for err in exc.errors():
            safe_errors.append(
                {
                    "loc": [str(part) for part in err.get("loc", [])],
                    "msg": err.get("msg"),
                    "type": err.get("type"),
                }
            )
        code_422 = (
            status.HTTP_422_UNPROCESSABLE_CONTENT
            if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT")
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        return JSONResponse(
            status_code=code_422,
            content={"detail": "Invalid request data", "errors": safe_errors},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_exception_handler(_: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Integrity error: %s", exc)
        return _error_response("Invalid request data", status.HTTP_409_CONFLICT)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        detail = "Internal server error" if not settings_debug() else f"Internal server error: {exc}"
        return _error_response(detail, status.HTTP_500_INTERNAL_SERVER_ERROR)


def settings_debug() -> bool:
    """Lazy import to avoid circular dependency at module load."""
    from backend.app.core.config import settings

    return settings.DEBUG
