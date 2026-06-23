"""API middleware.

Includes request ID correlation, rate limiting, and error normalization.
"""

from __future__ import annotations

from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.settings import settings


limiter = Limiter(key_func=get_remote_address)


# Register default rate limit. Routes can override using slowapi annotations.
# Using a global limiter instance keeps behavior consistent across the app.
def _rate_limit_string() -> str:
    return f"{settings.rate_limit_per_minute}/minute"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach X-Request-ID header for correlation."""

    async def dispatch(self, request: Request, call_next: Callable):
        request_id = request.headers.get("x-request-id")
        if not request_id:
            # Keep it simple and deterministic: fallback to a unique-ish value.
            request_id = f"req_{id(request)}"

        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a consistent response when rate limit is exceeded."""

    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded", "error": str(exc)},
        headers={"x-request-id": request.headers.get("x-request-id", "")},
    )

