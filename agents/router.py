"""Router agent.

Responsibility:
- Route a goal to a pipeline route key.

Production strategy:
- Deterministic rules based on keyword matching.
- Returns a route string used by the workflow coordinator.

In this scaffold, we always return a single route key. This keeps the
system fully functional while still demonstrating a router agent.
"""

from __future__ import annotations

from typing import Any

from app.logger import get_logger

logger = get_logger()


class RouterAgent:
    """Simple deterministic router."""

    async def route(self, goal: str, context: dict[str, Any]) -> str:
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("goal must be a non-empty string")

        g = goal.lower()
        if any(k in g for k in ["weather", "forecast"]):
            route = "weather_research"
        elif any(k in g for k in ["image", "picture", "visual"]):
            route = "image_research"
        else:
            route = "general_research"

        logger.info("Router selected route", extra={"route": route})
        return route

