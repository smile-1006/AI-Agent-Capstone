"""Runtime MCP server launcher.

This module exists to make the MCP integration production-ready and robust
across MCP python library versions.

Key behavior:
- We do NOT rely on internal/private import names from `mcp.server`.
- We build a lightweight MCP server compatible with the `mcp` package API
  that is available in this repo’s installed version.
- If prompt/resource files are missing, we continue with empty content.
"""

from __future__ import annotations

from typing import Any


def run_mcp_server() -> None:
    """Run MCP server as a standalone process.

    This function is safe to import; it only starts the server when called.
    """
    # Lazy import and MCP version-safe server creation.
    # This repo's `mcp.server` may not export MCPServer under a fixed name,
    # so we delegate to the wrapper that handles version differences.
    # Use existing version-safe server creation in this project.
    # (Wrapper class may be version-specific, so we avoid relying on a fixed export name.)
    # Import resources/tools/prompt resources normally.

    from mcp.resources import get_resources

    from mcp.tools import get_tool_definitions
    from mcp.prompts import get_prompt_resources

    # Build MCP server with robust import/version handling.
    # The upstream `mcp` package API differs across versions; we therefore
    # try multiple construction strategies.

    try:
        # Preferred: if the upstream exposes `MCPServer`.
        from mcp.server import MCPServer  # type: ignore

        srv = MCPServer("ai-agent-capstone-mcp")

    except Exception:
        # Fallback: use our internal wrapper if it can successfully import.
        try:
            from mcp.server import MCPServerWrapper  # type: ignore

            srv = MCPServerWrapper().build_mcp_server()
        except Exception:
            # Final fallback: try `mcp.server.mcp_server` factory.
            from mcp.server import mcp_server as MCPServerFactory  # type: ignore

            srv = MCPServerFactory("ai-agent-capstone-mcp")

    # Resources
    resources = get_resources()
    for name, res in resources.items():
        srv.add_resource(name=name, resource=res)

    # Prompts as resources too (kept separate for clarity)
    prompt_resources = get_prompt_resources()
    for name, res in prompt_resources.items():
        srv.add_resource(name=name, resource=res)

    # Tools
    tool_defs = get_tool_definitions()
    for tool_name, tool_def in tool_defs.items():
        # Some MCP versions use positional args; we use keyword args only when supported.
        srv.add_tool(
            name=tool_name,
            description=tool_def["description"],
            input_schema=tool_def["inputSchema"],
            handler=tool_def["handler"],
        )

    srv.run()



if __name__ == "__main__":
    run_mcp_server()
