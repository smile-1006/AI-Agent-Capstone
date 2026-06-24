from __future__ import annotations

from pathlib import Path
from typing import Any


async def read_text_file(ctx: Any, path: str, encoding: str = "utf-8") -> dict[str, Any]:
    """Read a local text file safely.

    This tool is offline-safe and only reads local filesystem paths.
    """

    if not isinstance(path, str) or not path.strip():
        raise ValueError("path must be a non-empty string")

    p = Path(path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"file not found: {path}")

    # Basic size guard to keep API responses bounded.
    stat = p.stat()
    if stat.st_size > 2_000_000:
        raise ValueError("file too large to read")

    content = p.read_text(encoding=encoding, errors="replace")
    return {"path": str(p), "size_bytes": int(stat.st_size), "content": content}

