"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env, resolved relative to this file so it works from any CWD.
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Central application settings.

    All secrets are supplied via environment variables (or backend/.env).
    """

    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Expense Tracker API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/expense_tracker"
    DB_ECHO: bool = False

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Auth cookie (centralized configuration; see app/core/cookies.py).
    # JWT_COOKIE_SECURE defaults to None (= auto): True when APP_ENV=production,
    # False otherwise. Set it explicitly for deployments that differ (e.g. an
    # HTTP-only staging box, or production behind TLS termination).
    JWT_COOKIE_NAME: str = "access_token"
    JWT_COOKIE_SECURE: bool | None = None
    JWT_COOKIE_HTTP_ONLY: bool = True
    JWT_COOKIE_SAMESITE: str = "lax"
    JWT_COOKIE_PATH: str = "/"
    JWT_COOKIE_DOMAIN: str | None = None

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # Testing (dedicated PostgreSQL test database)
    TEST_DATABASE_URL: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/expense_tracker_test"
    )

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        if value not in allowed:
            raise ValueError(f"APP_ENV must be one of {sorted(allowed)}")
        return value

    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def validate_token_expiry(cls, value: int) -> int:
        if value < 1 or value > 1440:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and 1440")
        return value

    @field_validator("JWT_COOKIE_SAMESITE")
    @classmethod
    def validate_cookie_samesite(cls, value: str) -> str:
        allowed = {"lax", "strict", "none"}
        if value.lower() not in allowed:
            raise ValueError(f"JWT_COOKIE_SAMESITE must be one of {sorted(allowed)}")
        return value.lower()

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def jwt_cookie_secure_effective(self) -> bool:
        """Resolve Secure flag: explicit env var wins, otherwise follow APP_ENV."""
        if self.JWT_COOKIE_SECURE is None:
            return self.is_production
        return self.JWT_COOKIE_SECURE

    @property
    def jwt_cookie_params(self) -> dict:
        """Keyword arguments for response.set_cookie/delete_cookie.

        Single source of truth so set and clear always agree on scope.
        """
        return {
            "key": self.JWT_COOKIE_NAME,
            "path": self.JWT_COOKIE_PATH,
            "domain": self.JWT_COOKIE_DOMAIN,
            "secure": self.jwt_cookie_secure_effective,
            "httponly": self.JWT_COOKIE_HTTP_ONLY,
            "samesite": self.JWT_COOKIE_SAMESITE,
        }


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
