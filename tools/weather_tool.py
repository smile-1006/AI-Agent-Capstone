from __future__ import annotations

from typing import Any


async def weather_offline(ctx: Any, location: str) -> dict[str, Any]:
    """Offline deterministic weather."""

    from mcp.tools import tool_weather

    return await tool_weather(ctx, location=location)

