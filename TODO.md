# AI-Agent-Capstone TODO

## Implement LLM integration (OpenRouter + NVIDIA) for real answers
- [x] Add LLM HTTP client module: `llm/client.py`
- [x] Add provider configuration fields to settings: `app/settings.py`
- [x] Load provider config from env: `app/bootstrap.py`
- [x] Update Planner to call LLM when configured + fallback deterministic mode: `agents/planner_agent.py`
- [x] Update Reviewer to call LLM when configured + fallback deterministic mode: `agents/reviewer_agent.py`
- [x] Add example env documentation: `README_LLM_EXAMPLE_ENV.md`

## Connectivity verification
- [x] Confirm frontend can call backend at `http://localhost:8000` (already using correct base URL)
- [x] Run backend and frontend locally and test `/api/execute` with LLM keys


