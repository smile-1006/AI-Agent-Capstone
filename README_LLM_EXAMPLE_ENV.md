# Example environment variables (OpenRouter + NVIDIA)

Copy the following into your `.env` file.

> Notes
> - Leave keys empty to use deterministic fallback (no LLM calls).
> - The app does not read `.env` here; this file is only documentation.

## Required (already used by backend)

```env
JWT_SECRET=change-me
```

## LLM selection

```env
# auto | openrouter | nvidia
LLM_PROVIDER=auto
```

## OpenRouter

```env
OPENROUTER_API_KEY=.....
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
# Example model id:
OPENROUTER_MODEL=openai/gpt-4o-mini
```

## NVIDIA

```env
NVIDIA_API_KEY=...
# Endpoint/path can vary by NVIDIA product/gateway.
NVIDIA_BASE_URL=https://api.nvidia.com/v1
# Example model id:
NVIDIA_MODEL=nvidia/llama-3.1-8b-instruct

# Optional override if your NVIDIA endpoint uses a different route
NVIDIA_CHAT_COMPLETIONS_PATH=chat/completions
```

## Optional runtime tuning

```env
# Used by planner/reviewer when generating temperature.
# (If not set, code uses 0.2 default)
# llm_temperature=0.2
```

