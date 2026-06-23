"""MCP prompts resources.

This module serves prompt text/config as MCP resources.
"""

from __future__ import annotations

from typing import Any

from app.logger import get_logger

logger = get_logger()



def _read_text_file(path: str) -> str:
    """Read a UTF-8 text file or return an empty string."""

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning("Prompt file not found: %s", path)
        return ""


def get_prompt_resources() -> dict[str, dict[str, Any]]:
    """Return prompt resources for the MCP server."""

    return {
        "prompts_planner": {
            "name": "prompts_planner",
            "type": "text",
            "content": _read_text_file("prompts/planner.txt"),
        },
        "prompts_researcher": {
            "name": "prompts_researcher",
            "type": "text",
            "content": _read_text_file("prompts/researcher.txt"),
        },
        "prompts_executor": {
            "name": "prompts_executor",
            "type": "text",
            "content": _read_text_file("prompts/executor.txt"),
        },
        "prompts_reviewer": {
            "name": "prompts_reviewer",
            "type": "text",
            "content": _read_text_file("prompts/reviewer.txt"),
        },
    }

