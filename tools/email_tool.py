from __future__ import annotations

from typing import Any


async def send_offline_email(ctx: Any, to: str, subject: str, body: str) -> dict[str, Any]:
    """Offline email sender (writes .eml to data/outbox/)."""

    from mcp.tools import tool_email

    return await tool_email(ctx, to=to, subject=subject, body=body)

