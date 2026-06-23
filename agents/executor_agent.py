"""Executor agent.

Responsibility:
- Take the plan + research evidence and produce a draft solution.

Production strategy:
- Deterministic synthesis (no LLM calls).
- Uses evidence snippets to construct a coherent response payload.
"""

from __future__ import annotations

from typing import Any

from app.logger import get_logger

logger = get_logger()


class ExecutorAgent:
    """Deterministic executor."""

    async def execute(
        self,
        plan: dict[str, Any],
        research: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        goal = plan.get("goal") or context.get("goal")
        steps = plan.get("steps") or []
        evidence = research.get("evidence") or []

        if not isinstance(evidence, list):
            raise ValueError("research.evidence must be a list")

        # Synthesize: include up to N evidence snippets.
        max_snippets = int(context.get("max_snippets", 5))
        max_snippets = max(1, min(max_snippets, 10))

        snippets: list[str] = []
        for item in evidence:
            query = item.get("query")
            results = item.get("results")
            if not results or not isinstance(results, list):
                continue
            first = results[0] if results else {}
            title = first.get("title") or ""
            snippet = first.get("snippet") or ""
            if title or snippet:
                snippets.append(f"{query}: {title} - {snippet}".strip(" -"))
            if len(snippets) >= max_snippets:
                break

        draft_text = {
            "goal": goal,
            "approach": "Deterministic synthesis using provided evidence.",
            "steps": steps,
            "key_points": snippets,
            "notes": "If web/network tools were unavailable, research may contain fallbacks.",
        }

        logger.info("Executor produced draft", extra={"goal": goal})

        return {
            "draft": draft_text,
            "used_evidence_count": len(snippets),
        }

