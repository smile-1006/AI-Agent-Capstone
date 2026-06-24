from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import uuid


@dataclass(frozen=True)
class ConversationTurn:
    id: str
    request_id: str
    role: str
    content: str
    created_at: str


class ConversationHistory:
    """Lightweight SQLite-backed conversation history.

    This is intentionally small and dependency-free (beyond stdlib) so that
    Kaggle/portfolio deployments remain reliable.

    Notes:
    - Agents in this repo already maintain deterministic in-memory history via
      `agents/memory_agent.py`. This class can be used by future/extended
      pipelines and by MCP tool handlers.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

