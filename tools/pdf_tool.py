from __future__ import annotations

from typing import Any


async def pdf_read(ctx: Any, path: str, max_pages: int = 3) -> dict[str, Any]:
    """Read PDF text from local disk."""

    from mcp.tools import tool_pdf_read

    return await tool_pdf_read(ctx, path=path, max_pages=max_pages)

