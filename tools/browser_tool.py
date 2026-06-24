from __future__ import annotations

from typing import Any


async def browser_file_url(ctx: Any, url: str) -> dict[str, Any]:
    """Offline browser for file:// URLs only."""

    from mcp.tools import tool_browser

    return await tool_browser(ctx, url=url)

