"""Agent execution use-cases exposed to the API layer."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from agents.executor_agent import ExecutorAgent
from agents.memory_agent import MemoryAgent
from agents.planner_agent import PlannerAgent
from agents.research_agent import ResearchAgent
from agents.reviewer_agent import ReviewerAgent
from agents.router import RouterAgent
from workflows.workflow import WorkflowCoordinator, WorkflowInput


@dataclass(frozen=True)
class ExecuteRequest:
    goal: str
    user: str | None
    request_id: str
    context: dict[str, Any]


class ExecuteUseCase:
    """Run the full agent pipeline."""

    def __init__(self) -> None:
        self._router = RouterAgent()
        self._planner = PlannerAgent()
        self._researcher = ResearchAgent(web_search_tool=None)
        self._executor = ExecutorAgent()
        self._reviewer = ReviewerAgent()
        self._memory = MemoryAgent()

        self._coordinator = WorkflowCoordinator(
            router=self._router,
            planner=self._planner,
            researcher=self._researcher,
            executor=self._executor,
            reviewer=self._reviewer,
        )

    async def __call__(self, goal: str, user: str | None, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("goal must be a non-empty string")

        request_id = (context or {}).get("request_id") or f"req_{uuid.uuid4().hex}"
        ctx = dict(context or {})
        ctx["request_id"] = request_id

        workflow_input = WorkflowInput(
            goal=goal.strip(),
            user=user,
            request_id=request_id,
            context=ctx,
        )

        # Store user's turn in memory (deterministic local memory)
        await self._memory.add_turn(request_id=request_id, turn={"role": "user", "content": goal.strip()})

        try:
            output = await self._coordinator.run(workflow_input)
        except Exception as e:
            # Surface LLM/provider failures to the frontend.
            return {
                "request_id": request_id,
                "route": None,
                "plan": None,
                "research": None,
                "draft": None,
                "final": None,
                "llm_error": str(e),
            }

        await self._memory.add_turn(
            request_id=request_id,
            turn={"role": "assistant", "content": output.final.get("final_answer")},
        )

        return {
            "request_id": request_id,
            "route": output.route,
            "plan": output.plan,
            "research": output.research,
            "draft": output.draft,
            "final": output.final,
        }


