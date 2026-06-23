"""Pydantic schemas for request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health status response."""

    status: str = Field(description="Health status")


