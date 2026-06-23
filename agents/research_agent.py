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

    async def research(self, plan: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Gather evidence for the provided plan."""

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

            # Offline fallback: provide a deterministic structured response
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

