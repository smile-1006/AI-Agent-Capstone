"""Workflow orchestration.

This module wires the core agent pipeline into a single callable.

Clean Architecture note:
- Agents are treated as application-level services
- This workflow coordinates use-cases, not persistence details

Currently, the agent implementations (planner/research/executor/reviewer/router/memory)
are not yet present in the repository. This file provides a stable orchestration
interface once those components are added.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class RouterAgent(Protocol):
    """Select which sub-workflow/strategy to run."""

    async def route(self, goal: str, context: dict[str, Any]) -> str:
        """Return a route key."""


class PlannerAgent(Protocol):
    async def plan(self, goal: str, context: dict[str, Any]) -> dict[str, Any]:
        """Return a plan object."""


class ResearchAgent(Protocol):
    async def research(self, plan: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Return gathered evidence."""


class ExecutorAgent(Protocol):
    async def execute(self, plan: dict[str, Any], research: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Return draft solution."""


class ReviewerAgent(Protocol):
    async def review(
        self,
        plan: dict[str, Any],
        draft: dict[str, Any],
        research: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Return reviewed final solution."""


@dataclass(frozen=True)
class WorkflowInput:
    goal: str
    user: str | None
    request_id: str
    context: dict[str, Any]


@dataclass(frozen=True)
class WorkflowOutput:
    route: str
    plan: dict[str, Any]
    research: dict[str, Any]
    draft: dict[str, Any]
    final: dict[str, Any]


class WorkflowCoordinator:
    """Orchestrates the full multi-agent pipeline."""

    def __init__(
        self,
        router: RouterAgent,
        planner: PlannerAgent,
        researcher: ResearchAgent,
        executor: ExecutorAgent,
        reviewer: ReviewerAgent,
    ) -> None:
        self._router = router
        self._planner = planner
        self._researcher = researcher
        self._executor = executor
        self._reviewer = reviewer

    async def run(self, workflow_input: WorkflowInput) -> WorkflowOutput:
        context = dict(workflow_input.context)
        context.setdefault("user", workflow_input.user)
        context.setdefault("request_id", workflow_input.request_id)

        route = await self._router.route(workflow_input.goal, context=context)
        plan = await self._planner.plan(workflow_input.goal, context=context)
        research = await self._researcher.research(plan=plan, context=context)
        draft = await self._executor.execute(plan=plan, research=research, context=context)
        final = await self._reviewer.review(plan=plan, draft=draft, research=research, context=context)

        return WorkflowOutput(
            route=route,
            plan=plan,
            research=research,
            draft=draft,
            final=final,
        )

