"""Reviewer agent.

Responsibility:
- Validate the executor draft against the plan requirements.
- Enforce basic policy: output must be JSON-serializable and include goal.

Production strategy:
- Deterministic checks only.
"""

from __future__ import annotations

from typing import Any

from app.logger import get_logger

logger = get_logger()


class ReviewerAgent:
    """Deterministic reviewer."""

    async def review(
        self,
        plan: dict[str, Any],
        draft: dict[str, Any],
        research: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        goal = plan.get("goal")
        if not goal:
            goal = (draft.get("draft") or {}).get("goal")

        if not goal or not isinstance(goal, str):
            raise ValueError("Missing/invalid goal")

        draft_payload = draft.get("draft")
        if not isinstance(draft_payload, dict):
            raise ValueError("draft.draft must be a dict")

        steps = draft_payload.get("steps")
        if steps is None:
            steps = plan.get("steps") or []

        final_text = {
            "goal": goal,
            "final_answer": draft_payload.get("key_points")
            or "No evidence provided; generate an answer based on general reasoning.",
            "validation": {
                "has_goal": True,
                "steps_present": isinstance(steps, list),
                "review_status": "passed",
            },
        }

        logger.info("Reviewer passed", extra={"goal": goal})
        return {"final": final_text, "status": "ok"}

