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
    """Plan the workflow from a user goal.

    If LLM is configured (OpenRouter or NVIDIA), this agent will use the
    provider to generate structured steps + sub_queries.

    Otherwise, it falls back to deterministic heuristics.
    """

    async def plan(self, goal: str, context: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("goal must be a non-empty string")

        # ---- LLM mode (optional) ----
        try:
            from app.settings import settings
            if settings.llm_provider.lower() in {"openrouter", "nvidia"}:
                from llm.client import call_nvidia_chat, call_openrouter_chat

                provider = settings.llm_provider.lower()

                messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are a planning assistant. "
                            "Return ONLY valid JSON with keys: goal, steps, sub_queries. "
                            "steps must be an array of 4-7 short strings. "
                            "sub_queries must be an array of 3-8 search-style queries."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Goal: {goal.strip()}\n\nReturn a plan for executing this goal.",
                    },
                ]

                temperature = float(context.get("llm_temperature", 0.2))

                if provider == "openrouter":
                    content = await call_openrouter_chat(
                        api_key=settings.openrouter_api_key,
                        base_url=settings.openrouter_base_url,
                        model=settings.openrouter_model,
                        messages=messages,
                        temperature=temperature,
                    )
                else:
                    content = await call_nvidia_chat(
                        api_key=settings.nvidia_api_key,
                        base_url=settings.nvidia_base_url,
                        model=settings.nvidia_model,
                        messages=messages,
                        temperature=temperature,
                        path=settings.nvidia_chat_completions_path,
                    )

                import json

                parsed = json.loads(content)
                # light validation
                steps = parsed.get("steps")
                sub_queries = parsed.get("sub_queries")
                if isinstance(steps, list) and isinstance(sub_queries, list):
                    plan_obj = Plan(
                        goal=str(parsed.get("goal") or goal.strip()),
                        steps=[str(s) for s in steps][:7],
                        sub_queries=[str(q) for q in sub_queries][:8],
                    )
                    logger.info("Planner LLM plan created", extra={"provider": provider})
                    return {
                        "goal": plan_obj.goal,
                        "steps": plan_obj.steps,
                        "sub_queries": plan_obj.sub_queries,
                    }
        except Exception as e:
            # If a provider is explicitly configured, do not silently fall back.
            try:
                from app.settings import settings

                provider = settings.llm_provider.lower()
            except Exception:
                provider = ""

            if provider in {"openrouter", "nvidia"}:
                raise

            logger.warning("Planner LLM failed; using fallback. err=%s", e)

        # If provider isn't configured (or LLM errors in non-LLM mode), continue with fallback


        # ---- Fallback deterministic mode ----

        topics = _extract_topics(goal)

        steps: list[str] = [
            "Clarify intent and constraints from the goal",
            "Identify required facts and likely data sources",
            "Gather evidence for each key sub-topic",
            "Synthesize a response aligned with the requested format",
            "Perform a final consistency and policy check",
        ]

        sub_queries: list[str]
        if topics:
            sub_queries = [f"latest information about {t}" for t in topics]
        else:
            sub_queries = ["key facts and definitions relevant to the goal"]

        logger.info("Planner created plan (fallback)", extra={"topics": topics})

        plan_obj = Plan(goal=goal.strip(), steps=steps, sub_queries=sub_queries)

        return {
            "goal": plan_obj.goal,
            "steps": plan_obj.steps,
            "sub_queries": plan_obj.sub_queries,
        }


