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

import re
from typing import Any

from app.logger import get_logger

logger = get_logger()


class RouterAgent:
    """Simple deterministic router."""

    def _extract_local_file_path(self, goal: str) -> str | None:
        if not isinstance(goal, str) or not goal.strip():
            return None

        file_match = re.search(
            r'"(?P<path>(?:file://|[A-Za-z]:(?:\\|/)|(?:\.\.?[\\/]|/))[^"\']+\.(?:pdf|docx|txt|png|jpe?g|gif|bmp|webp|tiff))"',
            goal,
            flags=re.IGNORECASE,
        )
        if file_match:
            return file_match.group('path').strip()

        file_match = re.search(
            r'(?P<path>(?:file://|[A-Za-z]:(?:\\|/)|(?:\.\.?[\\/]|/))[\S]+\.(?:pdf|docx|txt|png|jpe?g|gif|bmp|webp|tiff))',
            goal,
            flags=re.IGNORECASE,
        )
        if file_match:
            return file_match.group('path').strip()

        return None

    def _extract_search_query(self, goal: str) -> str | None:
        if not isinstance(goal, str) or not goal.strip():
            return None

        search_patterns = [
            r'web search(?: for| about)?\s+"([^"]+)"',
            r'web search(?: for| about)?\s+(.+)',
            r'search(?: for| about)?\s+"([^"]+)"',
            r'search(?: for| about)?\s+(.+)',
        ]

        for pattern in search_patterns:
            match = re.search(pattern, goal, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    async def route(self, goal: str, context: dict[str, Any]) -> str:
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("goal must be a non-empty string")

        path = self._extract_local_file_path(goal)
        if path:
            route = "file_research"
        elif any(k in goal.lower() for k in ["weather", "forecast"]):
            route = "weather_research"
        elif self._extract_search_query(goal) is not None or re.search(r'\b(find|lookup|browse)\b', goal, flags=re.IGNORECASE):
            route = "web_search"
        elif any(k in goal.lower() for k in ["image", "picture", "visual"]):
            route = "image_research"
        else:
            route = "general_research"

        logger.info("Router selected route", extra={"route": route})
        return route

