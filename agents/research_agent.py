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

        m = re.search(
            r"\b(?:in|at)\s+([A-Za-z][A-Za-z\s\-\']{1,60})[\.\?!]*\s*$",
            goal.strip(),
            flags=re.IGNORECASE,
        )
        if not m:
            return None

        loc = m.group(1).strip()
        return loc if loc else None

    def _extract_local_path_from_goal(self, goal: str) -> str | None:
        import re

        if not isinstance(goal, str) or not goal.strip():
            return None

        # Support quoted Windows/local paths with spaces, file:// URLs, and POSIX paths.
        path_match = re.search(
            r'["\'](?P<path>(?:file://|[A-Za-z]:(?:\\|/)|(?:\.\.?[\\/]|/))[^"\']+\.(?:pdf|docx|txt|png|jpe?g|gif|bmp|webp|tiff))["\']',
            goal,
            flags=re.IGNORECASE,
        )
        if path_match:
            return path_match.group('path').strip()

        path_match = re.search(
            r'(?P<path>(?:file://|[A-Za-z]:(?:\\|/)|(?:\.\.?[\\/]|/))[^\s,;]+\.(?:pdf|docx|txt|png|jpe?g|gif|bmp|webp|tiff))',
            goal,
            flags=re.IGNORECASE,
        )
        if path_match:
            return path_match.group('path').strip()

        return None

    def _extract_search_query_from_goal(self, goal: str) -> str | None:
        import re

        if not isinstance(goal, str) or not goal.strip():
            return None

        match = re.search(r'web search(?: for| about)?\s+"([^"]+)"', goal, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

        match = re.search(r'web search(?: for| about)?\s+(.+)', goal, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

        match = re.search(r'search(?: for| about)?\s+"([^"]+)"', goal, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

        match = re.search(r'search(?: for| about)?\s+(.+)', goal, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return None

    def _normalize_search_result(self, result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            title = result.get('title') or result.get('text') or result.get('snippet') or result.get('url') or ''
            snippet = result.get('snippet') or result.get('text') or result.get('title') or ''
            return {
                'title': str(title).strip(),
                'snippet': str(snippet).strip(),
                'url': result.get('url'),
            }

        return {
            'title': str(result),
            'snippet': str(result),
            'url': None,
        }

    def _normalize_search_results(self, results: list[Any]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in results:
            if item is None:
                continue
            normalized.append(self._normalize_search_result(item))
        return normalized

    def _excerpt_text(self, text: str, max_chars: int = 300) -> str:
        if not isinstance(text, str):
            return ""
        cleaned = " ".join(text.split())
        return cleaned[:max_chars].rstrip() + ("..." if len(cleaned) > max_chars else "")

    async def research(self, plan: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Gather evidence for the provided plan."""
        goal = plan.get("goal") or context.get("goal") or ""

        # ---- Local file / image path path: call appropriate tool directly -----
        local_path = self._extract_local_path_from_goal(goal)
        if local_path is not None:
            try:
                ext = local_path.split('?')[0].split('#')[0].rsplit('.', 1)[-1].lower()
            except Exception:
                ext = ''

            if ext == 'pdf':
                try:
                    from mcp.tools import tool_pdf_read

                    tool_result = await tool_pdf_read(ctx=context, path=local_path)
                    text = str(tool_result.get('text', '')).strip()
                    excerpt = self._excerpt_text(text, max_chars=400)
                    snippet = f"Read PDF at {local_path}: {tool_result.get('pages_read')} page(s). {excerpt}"
                    return {
                        "evidence": [
                            {
                                "query": f"pdf:{local_path}",
                                "results": [
                                    {
                                        "title": "PDF read tool result",
                                        "snippet": snippet,
                                        "url": None,
                                    }
                                ],
                                "tool": "pdf_read",
                                "fallback": False,
                            }
                        ],
                        "count": 1,
                    }
                except Exception as e:
                    logger.error("PDF research failed", exc_info=True)
                    return {
                        "evidence": [
                            {
                                "query": f"pdf:{local_path}",
                                "results": [
                                    {
                                        "title": "PDF tool execution failed",
                                        "snippet": str(e),
                                        "url": None,
                                    }
                                ],
                                "fallback": True,
                            }
                        ],
                        "count": 1,
                    }
            elif ext == 'docx' or ext == 'txt':
                try:
                    from mcp.tools import tool_document_read

                    tool_result = await tool_document_read(ctx=context, path=local_path)
                    text = str(tool_result.get('text', '')).strip()
                    excerpt = self._excerpt_text(text, max_chars=400)
                    snippet = f"Read document at {local_path}: {len(text.splitlines())} lines. {excerpt}"
                    return {
                        "evidence": [
                            {
                                "query": f"document:{local_path}",
                                "results": [
                                    {
                                        "title": "Document read tool result",
                                        "snippet": snippet,
                                        "url": None,
                                    }
                                ],
                                "tool": "document_read",
                                "fallback": False,
                            }
                        ],
                        "count": 1,
                    }
                except Exception as e:
                    logger.error("Document research failed", exc_info=True)
                    return {
                        "evidence": [
                            {
                                "query": f"document:{local_path}",
                                "results": [
                                    {
                                        "title": "Document tool execution failed",
                                        "snippet": str(e),
                                        "url": None,
                                    }
                                ],
                                "fallback": True,
                            }
                        ],
                        "count": 1,
                    }
            elif ext in {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff'}:
                try:
                    from mcp.tools import tool_image_ocr

                    tool_result = await tool_image_ocr(ctx=context, path=local_path, languages=['en'])
                    text = str(tool_result.get('text', '')).strip()
                    excerpt = self._excerpt_text(text, max_chars=400)
                    snippet = f"OCR extracted {len(tool_result.get('lines', []))} lines from {local_path}. {excerpt}"
                    return {
                        "evidence": [
                            {
                                "query": f"image_ocr:{local_path}",
                                "results": [
                                    {
                                        "title": "Image OCR result",
                                        "snippet": snippet,
                                        "url": None,
                                    }
                                ],
                                "tool": "image_ocr",
                                "fallback": False,
                            }
                        ],
                        "count": 1,
                    }
                except Exception as e:
                    logger.error("Image OCR research failed", exc_info=True)
                    return {
                        "evidence": [
                            {
                                "query": f"image_ocr:{local_path}",
                                "results": [
                                    {
                                        "title": "Image OCR execution failed",
                                        "snippet": str(e),
                                        "url": None,
                                    }
                                ],
                                "fallback": True,
                            }
                        ],
                        "count": 1,
                    }

        # ---- Web search path: call local or network search tool directly -----
        web_query = self._extract_search_query_from_goal(goal)
        if web_query is not None:
            try:
                from mcp.tools import tool_web_search

                results = await tool_web_search(ctx=context, query=web_query, max_results=5)
                normalized_results = self._normalize_search_results(results.get('results', []))
                return {
                    "evidence": [
                        {
                            "query": web_query,
                            "results": normalized_results,
                            "source": results.get('source'),
                            "tool": 'web_search',
                        }
                    ],
                    "count": 1,
                }
            except Exception as e:
                logger.error("Web search research failed", exc_info=True)
                return {
                    "evidence": [
                        {
                            "query": web_query,
                            "results": [
                                {
                                    "title": "Web search failed",
                                    "snippet": str(e),
                                    "url": None,
                                }
                            ],
                            "fallback": True,
                        }
                    ],
                    "count": 1,
                }

        # If the plan includes only a generic web-related string, use the plan goal as a fallback query.
        if "web search" in goal.lower() or "search" in goal.lower() or "browse" in goal.lower():
            try:
                from mcp.tools import tool_web_search

                results = await tool_web_search(ctx=context, query=goal.strip(), max_results=5)
                normalized_results = self._normalize_search_results(results.get('results', []))
                return {
                    "evidence": [
                        {
                            "query": goal.strip(),
                            "results": normalized_results,
                            "source": results.get('source'),
                            "tool": 'web_search',
                        }
                    ],
                    "count": 1,
                }
            except Exception as e:
                logger.error("Generic web search research failed", exc_info=True)
                return {
                    "evidence": [
                        {
                            "query": goal.strip(),
                            "results": [
                                {
                                    "title": "Generic web search failed",
                                    "snippet": str(e),
                                    "url": None,
                                }
                            ],
                            "fallback": True,
                        }
                    ],
                    "count": 1,
                }

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
                                    "title": "Tomorrow forecast",
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
                logger.error("Weather research failed", exc_info=True)
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
                    evidence.append({"query": query, "results": self._normalize_search_results(results if isinstance(results, list) else [])})
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

