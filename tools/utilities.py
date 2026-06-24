from __future__ import annotations

from typing import Any


def ensure_non_empty_str(value: Any, name: str) -> str:
    """Validate that `value` is a non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()

