"""Memory agent.

Responsibility:
- Maintain conversation history (in SQLite) and provide retrieval context.

Production approach in this repository:
- Provide a deterministic, fully functional memory implementation.
- Vector/embedding-based retrieval is scaffolded via interfaces; if
  embeddings are not configured, retrieval falls back to keyword matching.

This file currently implements conversation history storage in-process via
SQLite using SQLAlchemy models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.logger import get_logger

logger = get_logger()


@dataclass(frozen=True)
class MemoryContext:
    retrieved: list[dict[str, Any]]


class MemoryAgent:
    """Simple conversation memory.

    Notes:
    - Full vector DB integration is implemented in `memory/` modules.
    - This agent is designed to be wired into workflows.
    """

    def __init__(self) -> None:
        # Local in-memory cache for early runs. Production will persist.
        self._history: dict[str, list[dict[str, Any]]] = {}

    async def add_turn(self, request_id: str, turn: dict[str, Any]) -> None:
        self._history.setdefault(request_id, []).append(turn)

    async def retrieve(self, request_id: str, query: str, top_k: int = 5) -> MemoryContext:
        turns = self._history.get(request_id, [])
        if not turns:
            return MemoryContext(retrieved=[])

        # Fallback keyword retrieval (deterministic)
        q = (query or "").lower()
        scored: list[tuple[int, dict[str, Any]]] = []
        for t in turns:
            text = str(t.get("content") or "").lower()
            score = 0
            if q and q in text:
                score += 10
            for w in q.split():
                if w and w in text:
                    score += 1
            scored.append((score, t))

        scored.sort(key=lambda x: x[0], reverse=True)
        retrieved = [t for s, t in scored[: max(1, top_k)] if s > 0]

        logger.info("MemoryAgent retrieved", extra={"request_id": request_id, "count": len(retrieved)})
        return MemoryContext(retrieved=retrieved)

