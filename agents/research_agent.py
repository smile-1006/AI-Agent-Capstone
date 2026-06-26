"""Research agent.

Responsibility:
- Convert a plan and sub-queries into gathered evidence.

Production strategy in this repo:
- Deterministic + fully runnable implementation.
- When web browsing is available (via tools), this agent can use them.
- If network is not available (common in competitions), it falls back to
  lightweight offline research stubs based on the query text.

To keep the module production-ready and testable, all external calls are
isolated behind tool wrappers that validate inputs.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.logger import get_logger

logger = get_logger()


class WebSearchTool(Protocol):
    async def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:  # pragma: no cover
        ...


class ResearchAgent:
    """A research agent that can use optional web-search tooling."""

    def __init__(self, web_search_tool: WebSearchTool | None = None) -> None:
        self._web_search_tool = web_search_tool

    def _extract_location_from_goal(self, goal: str) -> str | None:
        """
        Heuristics:
        - "weather forecast for tomorrow in Chennai"
        - "tomorrow weather in London"
        - "weather in Paris"
        """
        import re

        if not isinstance(goal, str) or not goal.strip():
            return None

        m = re.search(r"\b(in|at)\s+([A-Za-z][A-Za-z\s\-\']{1,60})\s*$", goal.strip(), flags=re.IGNORECASE)
        if not m:
            return None

        loc = m.group(2).strip()
        return loc if loc else None

    async def research(self, plan: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Gather evidence for the provided plan."""
        goal = plan.get("goal") or context.get("goal") or ""

        # ---- Weather path: call local MCP tool directly (no MCP transport needed) ----
        g = str(goal).lower()
        if "weather" in g or "forecast" in g:
            location = context.get("location") or self._extract_location_from_goal(str(goal))
            if not location:
                # Default to Chennai so the frontend goal text works out of the box.
                location = "Chennai"


            try:
                from mcp.tools import tool_weather

                tool_result = await tool_weather(ctx=context, location=location)

                if "error" in tool_result:
                    err = tool_result["error"]
                    return {
                        "evidence": [
                            {
                                "query": goal,
                                "results": [
                                    {
                                        "title": "Weather provider error",
                                        "snippet": f"{err.get('type')}: {err.get('message')}",
                                        "url": None,
                                    }
                                ],
                                "fallback": True,
                            }
                        ],
                        "count": 1,
                    }

                forecast = tool_result.get("forecast") or {}
                conditions = forecast.get("conditions")
                tmin = forecast.get("temperature_min_c")
                tmax = forecast.get("temperature_max_c")
                humidity = forecast.get("humidity_percent")
                wind = forecast.get("wind_kph")
                source = forecast.get("source")

                snippet = (
                    f"{tool_result.get('location')} tomorrow: "
                    f"{conditions}, temp {tmin}..{tmax}°C, humidity {humidity}%, wind {wind} kph. "
                    f"(source: {source})"
                )

                return {
                    "evidence": [
                        {
                            "query": f"weather:{location}",
                            "results": [
                                {
                                    "title": "Tomorrow forecast (OpenWeatherMap)",
                                    "snippet": snippet,
                                    "url": None,
                                }
                            ],
                            "fallback": False,
                        }
                    ],
                    "count": 1,
                }
            except Exception as e:
                return {
                    "evidence": [
                        {
                            "query": goal,
                            "results": [
                                {
                                    "title": "Weather tool execution failed",
                                    "snippet": str(e),
                                    "url": None,
                                }
                            ],
                            "fallback": True,
                        }
                    ],
                    "count": 1,
                }

        # ---- Default path: original web-search/offline fallback evidence ----
        sub_queries: list[str] = plan.get("sub_queries") or []
        if not isinstance(sub_queries, list):
            raise ValueError("plan.sub_queries must be a list")

        max_results = int(context.get("max_results", 5))
        if max_results < 1 or max_results > 10:
            max_results = 5

        evidence: list[dict[str, Any]] = []

        for query in sub_queries[:8]:
            if not isinstance(query, str) or not query.strip():
                continue

            if self._web_search_tool is not None:
                try:
                    results = await self._web_search_tool.search(query=query, max_results=max_results)
                    evidence.append({"query": query, "results": results})
                    continue
                except Exception as e:
                    logger.warning("Web research failed; falling back. err=%s", e)

            evidence.append(
                {
                    "query": query,
                    "results": [
                        {
                            "title": f"Offline evidence for {query}",
                            "snippet": "Network/tooling not configured; using deterministic fallback.",
                            "url": None,
                        }
                    ],
                    "fallback": True,
                }
            )

        return {
            "evidence": evidence,
            "count": len(evidence),
        }

