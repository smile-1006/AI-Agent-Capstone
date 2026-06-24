from __future__ import annotations

from typing import Any

from tools.utilities import ensure_non_empty_str


async def safe_calculator(ctx: Any, expression: str) -> dict[str, Any]:
    """Evaluate a safe arithmetic expression.

    Wrapper around the deterministic logic in `mcp/tools.py`.
    """

    from mcp.tools import tool_calculator

    expression = ensure_non_empty_str(expression, "expression")
    return await tool_calculator(ctx, expression=expression)

