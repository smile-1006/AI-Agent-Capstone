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
import os
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
    cached corpus stored in `data/web_cache.txt` if present, and falls back
    to DuckDuckGo or a custom `web_search_api_url` if configured.
    """

    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not isinstance(max_results, int) or max_results < 1 or max_results > 10:
        raise ValueError("max_results must be an integer between 1 and 10")

    from app.settings import settings
    import httpx

    def _score_corpus(corpus: list[str]) -> list[str]:
        q = query.lower()
        scored: list[tuple[int, str]] = []
        for line in corpus:
            l = line.lower()
            if not l.strip():
                continue
            hits = sum(1 for tok in q.split() if tok and tok in l)
            if hits > 0:
                scored.append((hits, line))
        scored.sort(key=lambda t: (-t[0], t[1]))
        return [s[1] for s in scored[:max_results]]

    async def _call_json(url: str, params: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                raise RuntimeError(f"Request failed: {resp.status_code} {resp.text[:500]}")
            return resp.json()

    async def _duckduckgo_search() -> list[str]:
        data = await _call_json(
            "https://api.duckduckgo.com/",
            {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
        )
        results: list[str] = []
        if isinstance(data, dict):
            if text := data.get("AbstractText"):
                results.append(str(text).strip())
            for item in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(item, dict) and item.get("Text"):
                    results.append(str(item["Text"]).strip())
                elif isinstance(item, list):
                    for sub in item[:max_results]:
                        if isinstance(sub, dict) and sub.get("Text"):
                            results.append(str(sub["Text"]).strip())
                if len(results) >= max_results:
                    break
        return results[:max_results]

    cache_path = "data/web_cache.txt"
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            corpus = f.read().splitlines()
    except FileNotFoundError:
        corpus = []

    results = _score_corpus(corpus)
    source = "local_cache" if corpus else "none"

    if results:
        return {"query": query, "results": results, "source": source}

    if settings.web_search_api_url.strip():
        try:
            external_data = await _call_json(settings.web_search_api_url.strip(), {"q": query})
            if isinstance(external_data, dict):
                candidates = []
                for key in ("results", "items", "data", "hits"):
                    if key in external_data and isinstance(external_data[key], list):
                        candidates = external_data[key]
                        break
                if not candidates and "AbstractText" in external_data:
                    candidates = [external_data["AbstractText"]]
                results = [str(item) for item in candidates[:max_results]]
                if results:
                    return {"query": query, "results": results, "source": "external_api"}
        except Exception:
            pass

    try:
        results = await _duckduckgo_search()
        if results:
            return {"query": query, "results": results, "source": "duckduckgo"}
    except Exception:
        pass

    if not results:
        fallback = [f"No direct search results available for '{query}'."]
        return {"query": query, "results": fallback, "source": "fallback"}

    return {"query": query, "results": results[:max_results], "source": source}


async def tool_weather(ctx: Any, location: str) -> dict[str, Any]:
    """Weather tool using OpenWeatherMap or Open-Meteo fallback."""

    import re
    import math
    from datetime import datetime, timezone, timedelta

    import httpx

    if not isinstance(location, str) or not location.strip():
        raise ValueError("location must be a non-empty string")

    from app.settings import settings

    provider = settings.weather_provider.strip().lower() or "auto"
    openweather_key = settings.openweather_api_key.strip()
    openweather_geocode_url = settings.openweather_geocode_url.strip() or "https://api.openweathermap.org/geo/1.0/direct"
    openweather_forecast_url = settings.openweather_forecast_url.strip() or settings.weather_api_url.strip() or "https://api.openweathermap.org/data/2.5/forecast/daily"
    open_meteo_base_url = settings.open_meteo_base_url.strip() or "https://api.open-meteo.com/v1/forecast"
    open_meteo_geocode_url = settings.open_meteo_geocode_url.strip() or "https://geocoding-api.open-meteo.com/v1/search"

    loc = location.strip()
    lat_lon_match = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$", loc)
    resolved_name: str = loc

    def _preferred_sources() -> list[str]:
        if provider in {"open-meteo", "openmeteo"}:
            return ["open-meteo"]
        if provider in {"openweather", "openweathermap"}:
            return ["openweather", "open-meteo"]
        return ["openweather", "open-meteo"]

    async def _call_json(url: str, params: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params=params)
            if resp.status_code >= 400:
                response_text = resp.text
                raise RuntimeError(f"Request failed: {resp.status_code} {response_text[:500]}")
            return resp.json()

    async def _geocode_location() -> tuple[float, float, str]:
        nonlocal resolved_name

        if lat_lon_match:
            return float(lat_lon_match.group(1)), float(lat_lon_match.group(2)), loc

        if provider in {"auto", "openweather", "openweathermap"} and openweather_key:
            try:
                geocode = await _call_json(
                    openweather_geocode_url,
                    {"q": loc, "limit": 1, "appid": openweather_key},
                )
                if isinstance(geocode, list) and geocode:
                    first = geocode[0]
                    resolved_name = first.get("name") or loc
                    return float(first["lat"]), float(first["lon"]), resolved_name
            except Exception:
                pass

        geocode = await _call_json(
            open_meteo_geocode_url,
            {"name": loc, "count": 1},
        )
        results = geocode.get("results")
        if not isinstance(results, list) or not results:
            raise RuntimeError("No geocoding result found for the provided location")
        first = results[0]
        resolved_name = first.get("name") or loc
        return float(first["latitude"]), float(first["longitude"]), resolved_name

    async def _openweather_forecast(lat: float, lon: float) -> dict[str, Any]:
        if not openweather_key:
            raise RuntimeError("OPENWEATHER_API_KEY is not set")

        return await _call_json(
            openweather_forecast_url,
            {
                "lat": lat,
                "lon": lon,
                "cnt": 2,
                "units": "metric",
                "appid": openweather_key,
            },
        )

    async def _open_meteo_forecast(lat: float, lon: float) -> dict[str, Any]:
        return await _call_json(
            open_meteo_base_url,
            {
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,weathercode",
                "timezone": "UTC",
            },
        )

    async def _parse_openweather_response(forecast_data: dict[str, Any]) -> dict[str, Any]:
        list_days = forecast_data.get("list", [])
        if not isinstance(list_days, list) or len(list_days) < 1:
            raise RuntimeError("Unexpected OpenWeather forecast response shape.")

        tomorrow_utc = datetime.now(timezone.utc).date() + timedelta(days=1)
        chosen: dict[str, Any] | None = None
        for day in list_days:
            try:
                dt = int(day.get("dt"))
                day_date = datetime.fromtimestamp(dt, tz=timezone.utc).date()
                if day_date == tomorrow_utc:
                    chosen = day
                    break
            except Exception:
                continue

        if chosen is None:
            chosen = list_days[1] if len(list_days) >= 2 else list_days[0]

        temp_day = chosen.get("temp", {}).get("day")
        temp_min = chosen.get("temp", {}).get("min")
        temp_max = chosen.get("temp", {}).get("max")
        humidity = chosen.get("humidity")
        wind_speed = chosen.get("speed")
        weather0 = (chosen.get("weather") or [{}])[0]
        weather_main = weather0.get("main") or "Unknown"
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
            }
        }

    async def _parse_open_meteo_response(forecast_data: dict[str, Any]) -> dict[str, Any]:
        daily = forecast_data.get("daily") or {}
        dates = daily.get("time") or []
        temps_min = daily.get("temperature_2m_min") or []
        temps_max = daily.get("temperature_2m_max") or []
        weathercodes = daily.get("weathercode") or []

        if not dates or len(dates) < 2 or len(temps_min) < 2 or len(temps_max) < 2:
            raise RuntimeError("Open-Meteo returned incomplete daily forecast.")

        tomorrow_index = 1
        tmin = temps_min[tomorrow_index]
        tmax = temps_max[tomorrow_index]
        weather_code = (
            weathercodes[tomorrow_index]
            if len(weathercodes) > tomorrow_index
            else weathercodes[0]
            if weathercodes
            else None
        )
        condition_map = {
            0: "clear_sky",
            1: "mainly_clear",
            2: "partly_cloudy",
            3: "overcast",
            45: "fog",
            48: "depositing_rime_fog",
            51: "drizzle_light",
            53: "drizzle_moderate",
            55: "drizzle_dense",
            61: "rain_slight",
            63: "rain_moderate",
            65: "rain_heavy",
            71: "snow_slight",
            73: "snow_moderate",
            75: "snow_heavy",
            80: "rain_showers_slight",
            81: "rain_showers_moderate",
            82: "rain_showers_violent",
            95: "thunderstorm",
            99: "thunderstorm_hail",
        }
        conditions = condition_map.get(weather_code, str(weather_code))

        return {
            "forecast": {
                "day": "tomorrow",
                "temperature_c": (float(tmin) + float(tmax)) / 2,
                "temperature_min_c": float(tmin),
                "temperature_max_c": float(tmax),
                "humidity_percent": None,
                "wind_kph": None,
                "conditions": conditions,
                "source": "open-meteo",
                "note": "fetched from Open-Meteo daily forecast",
            }
        }

    try:
        lat, lon, resolved_name = await _geocode_location()
    except Exception as e:
        return {
            "location": location,
            "error": {"type": "geocode_failed", "message": str(e)},
        }

    forecast_data: dict[str, Any] | None = None
    forecast_source: str | None = None
    errors: list[str] = []

    for source in _preferred_sources():
        if source == "openweather":
            if not openweather_key:
                errors.append("OpenWeather skipped because OPENWEATHER_API_KEY is not set.")
                continue
            try:
                forecast_data = await _openweather_forecast(lat, lon)
                forecast_source = "openweather"
                break
            except Exception as exc:
                errors.append(f"OpenWeather failed: {exc}")
        elif source == "open-meteo":
            try:
                forecast_data = await _open_meteo_forecast(lat, lon)
                forecast_source = "open-meteo"
                break
            except Exception as exc:
                errors.append(f"Open-Meteo failed: {exc}")

    if forecast_data is None or forecast_source is None:
        return {
            "location": resolved_name,
            "error": {
                "type": "forecast_failed",
                "message": "; ".join(errors) or "No forecast source was available.",
            },
        }

    try:
        if forecast_source == "open-meteo":
            result = await _parse_open_meteo_response(forecast_data)
        else:
            result = await _parse_openweather_response(forecast_data)

        result["location"] = resolved_name
        return result
    except Exception as exc:
        return {
            "location": resolved_name,
            "error": {"type": "forecast_parse_failed", "message": str(exc)},
        }


async def tool_pdf_read(ctx: Any, path: str, max_pages: int = 3) -> dict[str, Any]:
    """Read a PDF from local disk.

    This is local-safe and uses `pypdf`.
    """

    if not isinstance(path, str) or not path.strip():
        raise ValueError("path must be a non-empty string")
    if not isinstance(max_pages, int) or max_pages < 1 or max_pages > 20:
        raise ValueError("max_pages must be an integer between 1 and 20")

    from pathlib import Path
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError, PdfStreamError
    import urllib.parse

    if isinstance(path, str) and path.startswith("file://"):
        path = urllib.parse.unquote(path[len("file://") :])

    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise ValueError(f"PDF file not found: {path}")

    if file_path.stat().st_size == 0:
        raise ValueError(f"PDF file is empty: {path}")

    try:
        reader = PdfReader(str(file_path))
    except (PdfReadError, PdfStreamError, ValueError) as exc:
        raise ValueError(f"Invalid or corrupted PDF file: {path}. {exc}") from exc

    pages = min(len(reader.pages), max_pages)
    text_parts: list[str] = []
    for i in range(pages):
        text_parts.append(reader.pages[i].extract_text() or "")

    text = "\n".join(text_parts).strip()
    return {"path": str(file_path), "pages_read": pages, "text": text}


async def tool_docx_read(ctx: Any, path: str) -> dict[str, Any]:
    """Read a DOCX document from local disk."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("path must be a non-empty string")

    from pathlib import Path
    from docx import Document
    import urllib.parse

    if path.startswith("file://"):
        path = urllib.parse.unquote(path[len("file://") :])

    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise ValueError(f"DOCX file not found: {path}")

    try:
        doc = Document(str(file_path))
    except Exception as exc:
        raise ValueError(f"Unable to read DOCX file: {path}. {exc}") from exc

    paragraphs = [p.text for p in doc.paragraphs if p.text]
    text = "\n".join(paragraphs).strip()
    return {"path": str(file_path), "paragraphs": len(paragraphs), "text": text}


async def tool_text_read(ctx: Any, path: str) -> dict[str, Any]:
    """Read a plain text file from local disk."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("path must be a non-empty string")

    from pathlib import Path
    import urllib.parse

    if path.startswith("file://"):
        path = urllib.parse.unquote(path[len("file://") :])

    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise ValueError(f"Text file not found: {path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read().strip()
    except Exception as exc:
        raise ValueError(f"Unable to read text file: {path}. {exc}") from exc

    return {"path": str(file_path), "text_length": len(text), "text": text}


async def tool_document_read(ctx: Any, path: str, max_pages: int = 3) -> dict[str, Any]:
    """Read a supported document from local disk."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("path must be a non-empty string")
    from pathlib import Path
    import urllib.parse

    if path.startswith("file://"):
        path = urllib.parse.unquote(path[len("file://") :])

    file_path = Path(path)
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        return await tool_pdf_read(ctx=ctx, path=str(file_path), max_pages=max_pages)
    if ext == ".docx":
        return await tool_docx_read(ctx=ctx, path=str(file_path))
    if ext == ".txt":
        return await tool_text_read(ctx=ctx, path=str(file_path))

    raise ValueError(f"Unsupported document type: {ext}. Supported: .pdf, .docx, .txt")


async def tool_image_ocr(ctx: Any, path: str, languages: list[str] | None = None) -> dict[str, Any]:
    """Extract text from a local image using OCR."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("path must be a non-empty string")
    if languages is None:
        languages = ["en"]
    if isinstance(languages, str):
        languages = [languages]
    if not isinstance(languages, (list, tuple)):
        raise ValueError("languages must be a list of language codes")

    from pathlib import Path
    from easyocr import Reader
    import urllib.parse

    if path.startswith("file://"):
        path = urllib.parse.unquote(path[len("file://") :])

    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise ValueError(f"Image file not found: {path}")

    reader = Reader(list(languages), gpu=False)
    results = reader.readtext(str(file_path), detail=0)
    text = "\n".join(str(item) for item in results).strip()
    return {"path": str(file_path), "languages": list(languages), "text": text, "lines": [str(item) for item in results]}


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
    import urllib.parse

    if isinstance(path, str) and path.startswith("file://"):
        path = urllib.parse.unquote(path[len("file://") :])

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
    "document_read": {
        "description": "Read local PDF/DOCX/TXT documents and return extracted text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_pages": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["path"],
        },
        "handler": tool_document_read,
    },
    "image_ocr": {
        "description": "Extract text from a local image using OCR.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "languages": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                    ]
                },
            },
            "required": ["path"],
        },
        "handler": tool_image_ocr,
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


