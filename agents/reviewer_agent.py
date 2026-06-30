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
    """Reviewer.

    If an LLM provider is configured, this agent will ask the model to produce
    a final answer and return it in the expected JSON shape.

    Otherwise, it falls back to deterministic validation.
    """

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
                            "You are a helpful assistant. "
                            "Given the plan, research evidence, and a draft, produce the best final answer. "
                            "Return ONLY plain text for the final answer (no JSON)."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Goal: {goal}\n\n"
                            f"Plan: {plan}\n\n"
                            f"Research: {research}\n\n"
                            f"Draft: {draft_payload}\n\n"
                            "Final answer:"
                        ),
                    },
                ]

                temperature = float(context.get("llm_temperature", 0.2))

                if provider == "openrouter":
                    final_answer = await call_openrouter_chat(
                        api_key=settings.openrouter_api_key,
                        base_url=settings.openrouter_base_url,
                        model=settings.openrouter_model,
                        messages=messages,
                        temperature=temperature,
                    )
                else:
                    final_answer = await call_nvidia_chat(
                        api_key=settings.nvidia_api_key,
                        base_url=settings.nvidia_base_url,
                        model=settings.nvidia_model,
                        messages=messages,
                        temperature=temperature,
                        path=settings.nvidia_chat_completions_path,
                    )

                final_text = {
                    "goal": goal,
                    "final_answer": final_answer.strip(),
                    "validation": {
                        "has_goal": True,
                        "steps_present": isinstance(steps, list),
                        "review_status": "llm-generated",
                    },
                }
                logger.info("Reviewer LLM final answer generated", extra={"provider": provider})
                return {"final": final_text, "status": "ok"}
        except Exception as e:
            try:
                from app.settings import settings
                provider = settings.llm_provider.lower()
            except Exception:
                provider = ""

            logger.warning("Reviewer LLM failed; falling back to deterministic final answer. err=%s", e)

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


