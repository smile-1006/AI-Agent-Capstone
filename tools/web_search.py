from __future__ import annotations

from typing import Any


async def web_search_offline(ctx: Any, query: str, max_results: int = 3) -> dict[str, Any]:
    """Offline deterministic web search using the local cache in `mcp/tools.py`."""

    from mcp.tools import tool_web_search

    return await tool_web_search(ctx, query=query, max_results=max_results)

