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


async def tool_web_search(ctx: Any, query: str, max_results: int = 3) -> dict[str, Any]:
    """Local-safe web search stub.

    Production capstone requirements request multiple tools. In this repo
    environment we must be runnable without external network access.

    This tool therefore performs a *best-effort* search over an optional
    cached corpus stored in `data/web_cache.txt` if present.
    """

    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not isinstance(max_results, int) or max_results < 1 or max_results > 10:
        raise ValueError("max_results must be an integer between 1 and 10")

    # Load optional local cache.
    cache_path = "data/web_cache.txt"
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            corpus = f.read().splitlines()
    except FileNotFoundError:
        corpus = []

    q = query.lower()
    scored: list[tuple[int, str]] = []
    for line in corpus:
        l = line.lower()
        if not l.strip():
            continue
        # Simple scoring: count query token hits.
        hits = sum(1 for tok in q.split() if tok and tok in l)
        if hits > 0:
            scored.append((hits, line))

    scored.sort(key=lambda t: (-t[0], t[1]))
    results = [s[1] for s in scored[:max_results]]

    return {"query": query, "results": results, "source": "local_cache" if corpus else "none"}


async def tool_weather(ctx: Any, location: str) -> dict[str, Any]:
    """Local-safe weather tool.

    Without external APIs, return a deterministic placeholder-free response
    derived from location hash.
    """

    import hashlib

    if not isinstance(location, str) or not location.strip():
        raise ValueError("location must be a non-empty string")

    h = hashlib.sha256(location.strip().lower().encode("utf-8")).hexdigest()
    # Derive plausible values deterministically.
    temp_c = int(h[:2], 16) - 10  # -10..245 -> clamp to -10..40
    temp_c = max(-10, min(40, temp_c))
    humidity = int(h[2:4], 16)  # 0..255 -> 20..95
    humidity = max(20, min(95, humidity))
    wind_kph = int(h[4:6], 16) % 60

    return {
        "location": location,
        "forecast": {
            "temperature_c": temp_c,
            "humidity_percent": humidity,
            "wind_kph": wind_kph,
            "conditions": "partly_cloudy",
            "note": "offline-deterministic (no external API configured)",
        },
    }


async def tool_pdf_read(ctx: Any, path: str, max_pages: int = 3) -> dict[str, Any]:
    """Read a PDF from local disk.

    This is local-safe and uses `pypdf`.
    """

    if not isinstance(path, str) or not path.strip():
        raise ValueError("path must be a non-empty string")
    if not isinstance(max_pages, int) or max_pages < 1 or max_pages > 20:
        raise ValueError("max_pages must be an integer between 1 and 20")

    from pypdf import PdfReader

    reader = PdfReader(path)
    pages = min(len(reader.pages), max_pages)
    text_parts: list[str] = []
    for i in range(pages):
        text_parts.append(reader.pages[i].extract_text() or "")

    text = "\n".join(text_parts).strip()
    return {"path": path, "pages_read": pages, "text": text}


async def tool_browser(ctx: Any, url: str) -> dict[str, Any]:
    """Local-safe browser tool.

    Without network access, we only allow reading from local files
    referenced via `file://` URLs.
    """

    if not isinstance(url, str) or not url.strip():
        raise ValueError("url must be a non-empty string")

    if url.startswith("file://"):
        import urllib.parse

        path = urllib.parse.unquote(url[len("file://") :])
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"url": url, "mode": "file", "content": content}

    raise ValueError("network browsing is disabled; use file:// URLs")


async def tool_image_process(ctx: Any, path: str, action: str = "info") -> dict[str, Any]:
    """Local-safe image processing.

    Supported actions: `info` (dimensions, format) and `thumbnail` (save derived image).
    """

    if not isinstance(path, str) or not path.strip():
        raise ValueError("path must be a non-empty string")
    if not isinstance(action, str) or action not in {"info", "thumbnail"}:
        raise ValueError("action must be one of: info, thumbnail")

    from PIL import Image
    import os

    img = Image.open(path)
    width, height = img.size
    img_format = img.format

    if action == "info":
        return {"path": path, "format": img_format, "width": width, "height": height}

    # thumbnail
    thumb_dir = os.path.join(os.path.dirname(path), "__thumbnails__")
    os.makedirs(thumb_dir, exist_ok=True)
    base = os.path.basename(path)
    thumb_path = os.path.join(thumb_dir, base)

    thumb = img.copy()
    thumb.thumbnail((256, 256))
    thumb.save(thumb_path)

    return {"path": path, "action": "thumbnail", "thumb_path": thumb_path, "width": width, "height": height}


async def tool_email(ctx: Any, to: str, subject: str, body: str) -> dict[str, Any]:
    """Local-safe email tool.

    Offline mode: write an RFC-like email to `data/outbox/` and return path.
    """

    import os
    import datetime as dt

    if not isinstance(to, str) or not to.strip():
        raise ValueError("to must be a non-empty string")
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("subject must be a non-empty string")
    if not isinstance(body, str) or not body.strip():
        raise ValueError("body must be a non-empty string")
    if len(subject) > 200 or len(body) > 20000:
        raise ValueError("email subject/body too large")

    out_dir = os.path.join("data", "outbox")
    os.makedirs(out_dir, exist_ok=True)

    ts = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    fname = f"email_{ts}.eml"
    path = os.path.join(out_dir, fname)

    content = (
        f"To: {to}\n"
        f"Subject: {subject}\n"
        f"Date: {ts}\n"
        "\n"
        f"{body}\n"
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return {"to": to, "subject": subject, "saved_to": path}



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
    "web_search": {
        "description": "Offline local-cache search over data/web_cache.txt (no network).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
        "handler": tool_web_search,
    },
    "weather": {
        "description": "Offline deterministic weather derived from location (no external API).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
            },
            "required": ["location"],
        },
        "handler": tool_weather,
    },
    "pdf_read": {
        "description": "Read local PDF text using pypdf.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_pages": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["path"],
        },
        "handler": tool_pdf_read,
    },
    "browser": {
        "description": "Offline browser for file:// URLs only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
            },
            "required": ["url"],
        },
        "handler": tool_browser,
    },
    "image": {
        "description": "Local image info/thumbnail via Pillow.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "action": {"type": "string", "enum": ["info", "thumbnail"]},
            },
            "required": ["path"],
        },
        "handler": tool_image_process,
    },
    "email": {
        "description": "Offline email sender that writes .eml to data/outbox/.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        },
        "handler": tool_email,
    },
}



def get_tool_definitions() -> dict[str, dict[str, Any]]:
    """Return MCP tool definitions.

    Kept as a function so callers can avoid import-time side effects.
    """

    return TOOL_DEFINITIONS


