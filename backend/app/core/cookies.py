"""Authentication cookie helpers.

Centralized so every place that touches the auth cookie uses the exact same
name, path, domain, and security flags (settings.jwt_cookie_params).
"""

from fastapi import Response

from backend.app.core.config import settings


def set_auth_cookie(response: Response, token: str) -> None:
    """Store the JWT access token in an HttpOnly cookie.

    The browser sends the cookie automatically; frontend JavaScript never
    needs (or gets) access to the token value.
    """
    response.set_cookie(
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **settings.jwt_cookie_params,
    )


def clear_auth_cookie(response: Response) -> None:
    """Remove the auth cookie using the same scope it was set with."""
    response.delete_cookie(**settings.jwt_cookie_params)
