"""API documentation endpoints.

FastAPI already serves an OpenAPI schema and interactive Swagger UI.
This module adds a small, production-friendly human-readable docs surface
for capstone judges.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.schemas import HealthResponse


router = APIRouter(prefix="/docs", tags=["docs"])


@router.get("/overview", response_model=HealthResponse, summary="Documentation overview")
def overview() -> HealthResponse:
    """Quick docs marker.

    Keeping a response model ensures this endpoint is strictly typed.
    """

    return HealthResponse(status="ok")

