from __future__ import annotations

import os
from typing import Any

import httpx

from app.logger import get_logger

logger = get_logger()


class LLMError(RuntimeError):
    pass


async def _post_chat_completions(
    *,
    base_url: str,
    api_key: str,
    path: str,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float = 0.2,
    timeout_s: int = 60,
) -> str:
    url = base_url.rstrip("/") + "/" + path.lstrip("/")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
                text = resp.text

    # OpenAI-compatible
    try:
        return data["choices"][0]["message"]["content"]
    except Exception as e:  # pragma: no cover
        raise LLMError(f"Unexpected LLM response shape: {data!r}") from e


async def call_openrouter_chat(
    *,
    api_key: str,
    base_url: str,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float = 0.2,
) -> str:

    if not api_key:
        raise LLMError("OPENROUTER_API_KEY is not set")

    return await _post_chat_completions(
        base_url=base_url,
        api_key=api_key,
        path="chat/completions",
        model=model,
        messages=messages,
        temperature=temperature,
    )


async def call_nvidia_chat(
    *,
    api_key: str,
    base_url: str,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float = 0.2,
    path: str | None = None,
) -> str:
    if not api_key:
        raise LLMError("NVIDIA_API_KEY is not set")

    # NVIDIA endpoint/path varies by product.
    # Allow overriding via env; otherwise default to OpenAI-compatible.
    chosen_path = path or os.environ.get("NVIDIA_CHAT_COMPLETIONS_PATH") or "chat/completions"

    return await _post_chat_completions(
        base_url=base_url,
        api_key=api_key,
        path=chosen_path,
        model=model,
        messages=messages,
        temperature=temperature,
    )

