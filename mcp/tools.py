"""MCP tools registry.

This module provides an allowlisted registry of tool call handlers.
The MCP server wrapper imports TOOL_REGISTRY.

All tool functions must be:
- async compatible (return awaitables)
- JSON-serializable outputs
- safe with strict input validation
"""

from __future__ import annotations

import math
from typing import Any, Awaitable, Callable


async def tool_calculator(ctx: Any, expression: str) -> dict[str, Any]:
    """Safely evaluate a math expression.

    Only supports numbers, whitespace, and operators +-*/().
    """

    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("expression must be a non-empty string")

    # Strict allowlist for characters.
    allowed = set("0123456789+-*/()., ")
    if any(ch not in allowed for ch in expression):
        raise ValueError("expression contains unsupported characters")

    # Evaluate using Python's eval with stripped builtins.
    # This is still risky for complex payloads, so we pre-filter characters.
    value = eval(expression, {"__builtins__": {}}, {})  # noqa: S307

    # Normalize floats to avoid JSON issues with NaN/inf.
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValueError("expression result is not finite")

    return {"expression": expression, "result": value}


async def tool_echo(ctx: Any, text: str) -> dict[str, Any]:
    """Echo back text (debug/testing tool)."""

    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if len(text) > 20000:
        raise ValueError("text too large")
    return {"text": text}


TOOL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "calculator": {
        "description": "Evaluate a safe arithmetic expression (supports +-*/().)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string"},
            },
            "required": ["expression"],
        },
        "handler": tool_calculator,
    },
    "echo": {
        "description": "Echo back text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
            },
            "required": ["text"],
        },
        "handler": tool_echo,
    },
}


def get_tool_definitions() -> dict[str, dict[str, Any]]:
    """Return MCP tool definitions.

    Kept as a function so callers can avoid import-time side effects.
    """

    return TOOL_DEFINITIONS


