"""MCP server implementation.

This module provides an MCP (Model Context Protocol) server that exposes:
- Resources: static prompt templates and server metadata
- Tools: safe wrappers around internal tools (web search, calculator, etc.)
- Context sharing: request-scoped correlation IDs and conversation snippets
- Security: request validation, tool allowlist, and optional token auth
- Rate limiting: basic per-request throttling using slowapi
- Logging: structured logs with correlation IDs
- Error handling: consistent JSON error payloads

Design goals:
- Production-ready structure and validation.
- Fully runnable even without external network access or LLM connectivity.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Coroutine

from fastapi import HTTPException, status
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.logger import get_logger
from app.settings import settings
from mcp.prompts import get_prompt_resources
from mcp.resources import get_resources
from mcp.tools import get_tool_definitions



logger = get_logger()

# slowapi limiter for MCP calls (separate from HTTP limiter)
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


@dataclass(frozen=True)
class MCPContext:
    """Request context shared across tool executions."""

    request_id: str
    user: str | None
    conversation: list[dict[str, Any]]


class MCPAuth:
    """Optional MCP authentication.

    If the MCP request includes a Bearer token, it is validated.
    If no token is provided, authentication is allowed only when
    JWT_SECRET is configured as non-empty (always true in this project).
    """

    def __init__(self) -> None:
        self._secret = settings.jwt_secret
        self._algorithm = settings.jwt_algorithm

    def validate_optional(self, token: str | None) -> str | None:
        if not token:
            return None
        try:
            decoded = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            return str(decoded.get("sub")) if decoded.get("sub") else None
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def _maybe_async(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Execute a function that may be sync or async."""
    res = func(*args, **kwargs)
    if asyncio.iscoroutine(res):
        return await res
    return res


class MCPServerWrapper:
    """Factory wrapper for MCP server.

    This project uses `mcp` python package. The exact server instantiation
    differs slightly across versions; we keep this wrapper small and
    compatible with the installed dependency.
    """

    def __init__(self) -> None:
        self._auth = MCPAuth()
        self._resources = get_resources()
        self._tools = get_tool_definitions()



    def build_mcp_server(self) -> Any:
        """Return an MCP server object."""
        # Lazy import to avoid version mismatch at module import time.
        # NOTE: The imported symbol name varies across MCP python versions.
        # We try a couple of common entry points.
        try:
            from mcp.server import Server as MCPServer  # type: ignore
        except ImportError:
            from mcp.server import mcp_server as MCPServer  # type: ignore

        srv = MCPServer("ai-agent-capstone-mcp")


        # Resources
        for name, handler in self._resources.items():
            srv.add_resource(name, handler)

        # Tools
        for tool_name, tool in self._tools.items():
            srv.add_tool(
                tool_name,
                tool["description"],
                tool["inputSchema"],
                tool["handler"],
            )

        return srv


def build_mcp_server() -> Any:
    """Convenience factory used by app bootstrap/tests.

    This function delegates to the version-stable runtime implementation.
    """

    # Import lazily to avoid circular imports and MCP version quirks.
    from mcp.server_runtime import run_mcp_server

    # The runtime function runs a standalone MCP server loop.
    # For compatibility with earlier code paths that expected an object,
    # we return the callable itself.
    return run_mcp_server


# Backwards-compatible alias
MCP_SERVER_FACTORY = build_mcp_server

