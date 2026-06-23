# TODO - AI-Agent-Capstone Production Build

## Phase 1: Scaffolding & Core Backend
- [ ] Create backend dependency manifests (requirements.txt) if missing
- [ ] Create `.env.example`
- [ ] Create `app/` core: `settings.py`, `config.py`, `logger.py`
- [ ] Create FastAPI entrypoint `app/main.py`
- [ ] Create API layer: `api/routes.py`, `api/schemas.py`, `api/auth.py`, `api/middleware.py`
- [ ] Create DB layer: `database/models.py`, session management/migrations hooks
- [ ] Add tests baseline: `tests/test_api.py`, etc.

## Phase 2: Agents, Tools, Memory
- [ ] Implement agent interfaces and agents:
  - [ ] `agents/planner_agent.py`
  - [ ] `agents/research_agent.py`
  - [ ] `agents/executor_agent.py`
  - [ ] `agents/reviewer_agent.py`
  - [ ] `agents/memory_agent.py`
  - [ ] `agents/router.py`
- [ ] Implement tools wrappers in `tools/`:
  - [ ] web_search
  - [ ] calculator
  - [ ] file_reader
  - [ ] pdf_tool
  - [ ] browser_tool
  - [ ] weather_tool
  - [ ] image_tool
  - [ ] email_tool
- [ ] Implement memory subsystem in `memory/`:
  - [ ] `vector_store.py`
  - [ ] `embeddings.py`
  - [ ] `retrieval.py`
  - [ ] `history.py`
- [ ] Implement workflows:
  - [ ] `workflows/planner.py`
  - [ ] `workflows/executor.py`
  - [ ] `workflows/validator.py`
  - [ ] `workflows/workflow.py`

## Phase 3: MCP Server
- [ ] Implement `mcp/` server:
  - [ ] `mcp/server.py`
  - [ ] `mcp/resources.py`
  - [ ] `mcp/tools.py`
  - [ ] `mcp/prompts.py`
- [ ] Add MCP security: auth, tool allowlist, input validation, rate limiting, logging

## Phase 4: Frontend
- [ ] Scaffold React app structure under `frontend/`
- [ ] Implement API client + auth
- [ ] Implement chat UI + conversation history
- [ ] Add Tailwind styling and components

## Phase 5: Documentation, Diagrams, Testing, Deployment
- [ ] Expand README.md with setup/run/docs
- [ ] Add diagram artifacts under docs/
- [ ] Implement full unit/integration/error tests
- [ ] Add Dockerfile + docker-compose
- [ ] Add GitHub Actions CI workflow
- [ ] Add deployment configs (render.yaml, railway.json)
- [ ] Final smoke tests: backend + frontend + MCP

