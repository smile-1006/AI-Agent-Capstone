"""Tools package.

Dockerfile expects a top-level `tools/` directory.

The actual tool implementations for the MCP server live in `mcp/tools.py`.
These modules provide thin, production-safe wrappers so the backend image
builds cleanly and tool execution remains deterministic/offline.
"""

from .calculator import safe_calculator
from .web_search import web_search_offline
from .pdf_tool import pdf_read
from .browser_tool import browser_file_url
from .weather_tool import weather_offline
from .image_tool import image_info, image_thumbnail
from .email_tool import send_offline_email

__all__ = [
    "safe_calculator",
    "web_search_offline",
    "pdf_read",
    "browser_file_url",
    "weather_offline",
    "image_info",
    "image_thumbnail",
    "send_offline_email",
]

