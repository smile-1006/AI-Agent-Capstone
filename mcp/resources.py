"""MCP resources.

MCP resources are read-only pieces of context/config that the client can fetch.

In this capstone project, resources include:
- System prompt / policy text
- Planner/research/executor/reviewer prompts
- Optional runtime metadata
"""

from __future__ import annotations

from typing import Any

from app.logger import get_logger

logger = get_logger()



def _read_text_file(path: str) -> str:
    """Read a text file with a safe fallback.

    If the file doesn't exist (during early scaffolding), return an empty string.
    This keeps the server importable and runnable.
    """

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning("Resource file not found: %s", path)
        return ""


def get_resources() -> dict[str, dict[str, Any]]:
    """Return MCP resources.

    The server wrapper in `mcp/server.py` expects a dict keyed by resource name.
    Each value is a small dict describing the resource.

    MCP transport/library may ignore some fields depending on version; we
    keep the structure simple and JSON-serializable.
    """

    system_prompt = _read_text_file("prompts/system_prompt.txt")

    return {
        "system_prompt": {
            "name": "system_prompt",
            "type": "text",
            "content": system_prompt,
        },
        "runtime": {
            "name": "runtime",
            "type": "json",
            "content": {
                "capstone": True,
            },
        },
    }

