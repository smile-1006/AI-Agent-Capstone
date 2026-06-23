# Architecture (Clean Architecture)

This project is organized using a Clean Architecture-inspired layering.

## Layers

### API (Delivery)
- `api/routes.py`: HTTP endpoints (FastAPI).
- `api/schemas.py`: Pydantic request/response models.
- `api/auth.py`: Authentication utilities (JWT + password hashing).
- `api/middleware.py`: Request ID + rate limiting + error normalization.
- `api/execution.py`: API-level use case that runs the agent pipeline.

### Application (Use Cases / Orchestration)
- `workflows/workflow.py`: `WorkflowCoordinator` orchestrating agent calls.
- `agents/*_agent.py`: Deterministic agent implementations for planner/research/executor/reviewer/router.
- `agents/memory_agent.py`: Conversation memory abstraction.

### Infrastructure (Persistence / External systems)
- `database/*`: SQLAlchemy models + session creation.
- `mcp/*`: MCP server runtime/resources/tools.

### Configuration & Observability
- `app/settings.py`, `app/bootstrap.py`: strongly-typed settings.
- `app/logger.py`: structured logging.

## Request flow
1. Client calls `POST /api/execute` with a goal.
2. `api/routes.py` instantiates `ExecuteUseCase`.
3. `ExecuteUseCase`:
   - stores user turn in memory
   - builds `WorkflowInput`
   - calls `WorkflowCoordinator.run()`
4. `WorkflowCoordinator` executes:
   - RouterAgent -> PlannerAgent -> ResearchAgent -> ExecutorAgent -> ReviewerAgent
5. Result is returned as JSON.

## Security
- `/api/auth/*` provides JWT issuance.
- `api/auth.py` supports verifying tokens.
- MCP server has optional token validation and rate limiting.

## Notes about determinism
To ensure Kaggle-capstone execution reliability, agents are deterministic and
avoid requiring external LLM/network access. Tool-based enrichment can be
plugged in via wrappers where configured.

