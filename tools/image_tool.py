from __future__ import annotations

from typing import Any


async def image_info(ctx: Any, path: str) -> dict[str, Any]:
    """Return image metadata."""

    from mcp.tools import tool_image_process

    return await tool_image_process(ctx, path=path, action="info")


async def image_thumbnail(ctx: Any, path: str) -> dict[str, Any]:
    """Create a thumbnail and return details."""

    from mcp.tools import tool_image_process

    return await tool_image_process(ctx, path=path, action="thumbnail")

