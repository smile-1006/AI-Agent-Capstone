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
    """Weather tool using OpenWeatherMap.

    Returns a deterministic structure including "tomorrow" forecast extracted
    from the OpenWeatherMap "daily forecast" endpoint.

    If OPENWEATHER_API_KEY is missing or the request fails, this tool returns
    an error payload (it will NOT silently return offline deterministic data).
    """

    import os
    import re
    import math
    from datetime import datetime, timezone

    import httpx

    if not isinstance(location, str) or not location.strip():
        raise ValueError("location must be a non-empty string")

    api_key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    if not api_key:
        return {
            "location": location,
            "error": {
                "type": "missing_api_key",
                "message": "OPENWEATHER_API_KEY is not set",
            },
        }

    geocode_url = os.environ.get(
        "OPENWEATHER_GEOCODE_URL", "https://api.openweathermap.org/geo/1.0/direct"
    ).strip()
    forecast_url = os.environ.get(
        "WEATHER_API_URL", "https://api.openweathermap.org/data/2.5/forecast/daily"
    ).strip()

    loc = location.strip()
    # Support "lat,lon"
    lat_lon_match = re.match(
        r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$", loc
    )
    lat: float | None = None
    lon: float | None = None
    resolved_name: str = loc

    async def _call_json(url: str, params: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"OpenWeatherMap request failed: {resp.status_code} {resp.text[:500]}"
                )
            return resp.json()

    try:
        if lat_lon_match:
            lat = float(lat_lon_match.group(1))
            lon = float(lat_lon_match.group(2))
        else:
            geocode = await _call_json(
                geocode_url,
                {"q": loc, "limit": 1, "appid": api_key},
            )
            if not isinstance(geocode, list) or not geocode:
                return {
                    "location": location,
                    "error": {
                        "type": "geocode_failed",
                        "message": "No geocoding result found for the provided location",
                    },
                }
            first = geocode[0]
            lat = float(first["lat"])
            lon = float(first["lon"])
            resolved_name = first.get("name") or loc

        # Daily endpoint is count-based (cnt). We ask for tomorrow plus today.
        # We then choose "tomorrow" by date, using the forecast item's dt.
        # Units: metric (°C), wind km/h (OpenWeather metric default).
        daily = await _call_json(
            forecast_url,
            {
                "lat": lat,
                "lon": lon,
                "cnt": 2,
                "units": "metric",
                "appid": api_key,
            },
        )

        list_days = daily.get("list", [])
        if not isinstance(list_days, list) or len(list_days) < 1:
            return {
                "location": location,
                "error": {
                    "type": "forecast_parse_failed",
                    "message": "Unexpected forecast response shape (missing list)",
                },
            }

        tomorrow_utc = datetime.now(timezone.utc).date().fromtimestamp(
            datetime.now(timezone.utc).timestamp() + 24 * 3600
        )

        chosen = None
        for day in list_days:
            try:
                dt = int(day.get("dt"))
                day_date = datetime.fromtimestamp(dt, tz=timezone.utc).date()
                if day_date == tomorrow_utc:
                    chosen = day
                    break
            except Exception:
                continue

        # Fallback: if response doesn't align to UTC date, take second item when available.
        if chosen is None:
            chosen = list_days[1] if len(list_days) >= 2 else list_days[0]

        # Extract fields
        temp_day = chosen.get("temp", {}).get("day")
        temp_min = chosen.get("temp", {}).get("min")
        temp_max = chosen.get("temp", {}).get("max")

        humidity = chosen.get("humidity")
        wind_speed = chosen.get("speed")  # metric typically km/h
        weather0 = (chosen.get("weather") or [{}])[0]
        weather_main = weather0.get("main") or "Unknown"

        # Simple condition mapping
        condition_map = {
            "Clear": "clear_sky",
            "Clouds": "cloudy",
            "Rain": "rain",
            "Drizzle": "drizzle",
            "Thunderstorm": "thunderstorms",
            "Snow": "snow",
            "Mist": "mist",
            "Smoke": "smoke",
            "Haze": "haze",
            "Fog": "fog",
        }
        conditions = condition_map.get(str(weather_main), str(weather_main).lower())

        # Normalize temperatures to floats if possible
        def _to_float(x: Any) -> float | None:
            try:
                if x is None:
                    return None
                v = float(x)
                if math.isnan(v) or math.isinf(v):
                    return None
                return v
            except Exception:
                return None

        tday = _to_float(temp_day)
        tmin = _to_float(temp_min)
        tmax = _to_float(temp_max)

        temp_out: float | None = tday
        if temp_out is None and tmin is not None and tmax is not None:
            temp_out = (tmin + tmax) / 2.0

        return {
            "location": resolved_name,
            "forecast": {
                "day": "tomorrow",
                "temperature_c": temp_out,
                "temperature_min_c": tmin,
                "temperature_max_c": tmax,
                "humidity_percent": humidity if isinstance(humidity, (int, float)) else None,
                "wind_kph": wind_speed if isinstance(wind_speed, (int, float)) else None,
                "conditions": conditions,
                "source": "openweathermap",
                "note": "fetched from OpenWeatherMap (daily forecast)",
            },
        }
    except Exception as e:
        return {
            "location": location,
            "error": {
                "type": "openweathermap_error",
                "message": str(e),
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
        "description": "OpenWeatherMap weather forecast tool (tomorrow). Accepts city name or 'lat,lon'.",
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


