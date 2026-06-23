"""Configuration helpers.

This module centralizes non-settings constants and small helper functions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppMeta:
    """Static app metadata."""

    name: str = "AI-Agent-Capstone"
    version: str = "0.1.0"


app_meta = AppMeta()

