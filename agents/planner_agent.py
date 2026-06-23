"""Planner agent.

Responsibility:
- Convert a user goal into a structured plan and sub-queries.

Production notes:
- This implementation is local-only (no LLM calls) to keep the project
  fully runnable in the competition environment.
- It uses deterministic heuristics + prompt-template text (if present) to
  produce a plan object that downstream agents can refine.

This design keeps the agent module production-ready and testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.logger import get_logger

logger = get_logger()


@dataclass(frozen=True)
class Plan:
    """Structured plan for downstream steps."""

    goal: str
    steps: list[str]
    sub_queries: list[str]


def _extract_topics(goal: str) -> list[str]:
    """Extract candidate topics from the goal.

    Heuristic: words longer than 3 chars, excluding stopwords.
    """

    stop = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "into",
        "your",
        "you",
        "are",
        "was",
        "were",
        "will",
        "can",
        "should",
        "would",
        "could",
        "a",
        "an",
        "to",
        "of",
        "in",
        "on",
        "at",
        "as",
        "by",
        "be",
        "or",
        "not",
    }

    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", goal.lower())
    topics: list[str] = []
    for w in words:
        if w in stop:
            continue
        if w not in topics:
            topics.append(w)
    return topics[:7]


class PlannerAgent:
    """Deterministic planner implementation."""

    async def plan(self, goal: str, context: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("goal must be a non-empty string")

        topics = _extract_topics(goal)

        steps: list[str] = [
            "Clarify intent and constraints from the goal",
            "Identify required facts and likely data sources",
            "Gather evidence for each key sub-topic",
            "Synthesize a response aligned with the requested format",
            "Perform a final consistency and policy check",
        ]

        sub_queries = []
        if topics:
            for t in topics:
                sub_queries.append(f"latest information about {t}")
        else:
            sub_queries = ["key facts and definitions relevant to the goal"]

        logger.info("Planner created plan", extra={"topics": topics})

        plan_obj = Plan(goal=goal.strip(), steps=steps, sub_queries=sub_queries)

        return {
            "goal": plan_obj.goal,
            "steps": plan_obj.steps,
            "sub_queries": plan_obj.sub_queries,
        }

