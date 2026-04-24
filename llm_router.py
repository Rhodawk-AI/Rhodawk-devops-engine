"""
Rhodawk AI — Universal LLM Router
=================================
DO-primary, OpenRouter-fallback chat-completion router that every component
can call without knowing which provider is up. Works as a drop-in for any
existing OpenAI-style call site.

Public surface
--------------
    chat(role, messages, *, json_mode=True, temperature=0.2,
         max_tokens=2048, timeout=120) -> dict | str

    chat_text(role, messages, ...) -> str
    chat_json(role, messages, ...) -> dict

Each role string is resolved against ``model_squad.SquadModel`` to pick the
correct DO model id (primary) and OpenRouter id (fallback). The router
honours rate-limit 429 with a small backoff before failing over.

Set ``RHODAWK_LLM_DEBUG=1`` to see provider routing on stderr.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any

import requests

import model_squad

LOG = logging.getLogger("rhodawk.llm_router")

DEBUG = os.getenv("RHODAWK_LLM_DEBUG", "0") == "1"

# Backoff windows (seconds) tried inside one provider before moving on.
_RATE_LIMIT_BACKOFF = (3, 8, 20)


class LLMUnavailableError(RuntimeError):
    """Raised when neither DO nor OpenRouter can serve the request."""


def _dbg(msg: str) -> None:
    if DEBUG:
        print(f"[llm_router] {msg}", file=sys.stderr, flush=True)


def _post(base_url: str, api_key: str, model: str, messages: list[dict],
          json_mode: bool, temperature: float, max_tokens: int,
          timeout: int, extra_headers: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def _try_provider(name: str, base_url: str, api_key: str, model: str,
                  messages: list[dict], json_mode: bool, temperature: float,
                  max_tokens: int, timeout: int,
                  extra_headers: dict | None = None) -> dict | None:
    """Returns the raw chat-completion JSON, or None on a non-recoverable
    failure that should trigger fallback to the next provider."""
    if not api_key:
        return None
    for attempt, wait in enumerate((0,) + _RATE_LIMIT_BACKOFF):
        if wait:
            _dbg(f"{name} 429 backoff {wait}s (attempt {attempt})")
            time.sleep(wait)
        try:
            _dbg(f"→ {name} :: {model}")
            return _post(base_url, api_key, model, messages, json_mode,
                         temperature, max_tokens, timeout, extra_headers)
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            if status == 429:
                continue  # try next backoff
            _dbg(f"{name} HTTP {status} — {e}")
            return None
        except Exception as exc:  # noqa: BLE001 — fall over to next provider
            _dbg(f"{name} exception — {exc}")
            return None
    _dbg(f"{name} exhausted retries")
    return None


def chat(role: str, messages: list[dict], *, json_mode: bool = True,
         temperature: float = 0.2, max_tokens: int = 2048,
         timeout: int = 120) -> dict:
    """Run a chat completion through the squad. Returns the raw provider
    response dict (OpenAI-compatible).

    Order of attempts:
      1. DigitalOcean Serverless Inference (DO_INFERENCE_API_KEY)
      2. OpenRouter (OPENROUTER_API_KEY)

    Raises LLMUnavailableError if both providers fail or are unconfigured.
    """
    sq = model_squad.get(role)

    # PRIMARY — DigitalOcean. Skip if DO does not host this particular role.
    if sq.on_do:
        result = _try_provider(
            "DigitalOcean",
            model_squad.DO_INFERENCE_BASE_URL,
            model_squad.DO_INFERENCE_API_KEY,
            sq.do_id,
            messages, json_mode, temperature, max_tokens, timeout,
        )
        if result is not None:
            return result

    # FALLBACK — OpenRouter.
    result = _try_provider(
        "OpenRouter",
        model_squad.OPENROUTER_BASE_URL,
        model_squad.OPENROUTER_API_KEY,
        sq.or_id,
        messages, json_mode, temperature, max_tokens, timeout,
        extra_headers={
            "HTTP-Referer": "https://rhodawk.ai",
            "X-Title": f"Rhodawk {role}",
        },
    )
    if result is not None:
        return result

    raise LLMUnavailableError(
        f"role={role}: neither DO nor OpenRouter could serve the request"
    )


def chat_text(role: str, messages: list[dict], **kwargs) -> str:
    """Convenience wrapper that returns just the assistant's text content."""
    kwargs.setdefault("json_mode", False)
    raw = chat(role, messages, **kwargs)
    try:
        return raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMUnavailableError(f"unexpected response shape: {e}") from e


def chat_json(role: str, messages: list[dict], **kwargs) -> dict:
    """Convenience wrapper that returns the assistant's content parsed as JSON.
    Falls back to ``{"raw": <text>}`` if the model violated json_mode."""
    kwargs.setdefault("json_mode", True)
    raw = chat(role, messages, **kwargs)
    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMUnavailableError(f"unexpected response shape: {e}") from e
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return {"raw": content}


if __name__ == "__main__":
    print(model_squad.describe())
