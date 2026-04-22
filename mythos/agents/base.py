"""
Base agent class for the Mythos multi-agent framework.

All Mythos agents share:
  * a ``name`` used in routing / logging
  * a ``model_tier`` (``"tier1"`` strategy / ``"tier2"`` execution / ``"tier3"`` consensus)
  * a tool-calling client that maps to OpenRouter / vLLM / TGI etc.
  * a structured ``act(context)`` entry point returning a typed message
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

import requests

LOG = logging.getLogger("mythos.agent")

# ---------------------------------------------------------------------------
# Tier → model resolution.  All values can be overridden by env vars so the
# operator can swap in vLLM / TGI / Ollama endpoints without touching code.
# ---------------------------------------------------------------------------

_DEFAULT_MODELS = {
    "tier1": [
        os.getenv("MYTHOS_TIER1_PRIMARY", "deepseek/deepseek-v2-chat"),
        os.getenv("MYTHOS_TIER1_FALLBACK", "qwen/qwen-2-72b-instruct"),
        "mistralai/mixtral-8x22b-instruct",
    ],
    "tier2": [
        os.getenv("MYTHOS_TIER2_PRIMARY", "qwen/qwen-2.5-coder-72b-instruct"),
        os.getenv("MYTHOS_TIER2_FALLBACK", "codellama/codellama-70b-instruct"),
    ],
    "tier3": [
        "meta-llama/llama-3.3-70b-instruct",
        "deepseek/deepseek-v3",
        "google/gemma-2-27b-it",
    ],
}


def models_for_tier(tier: str) -> list[str]:
    return list(_DEFAULT_MODELS.get(tier, _DEFAULT_MODELS["tier1"]))


@dataclass
class AgentMessage:
    sender: str
    recipient: str
    role: str  # "request" | "response" | "broadcast" | "tool"
    content: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(self.__dict__, default=str)


class MythosAgent:
    """Concrete agents subclass this and implement ``act()``."""

    name: str = "agent"
    model_tier: str = "tier1"

    def __init__(self, openrouter_key: str | None = None, base_url: str | None = None):
        self.openrouter_key = openrouter_key or os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = base_url or os.getenv(
            "MYTHOS_LLM_BASE", "https://openrouter.ai/api/v1"
        )

    # -- tool-calling -------------------------------------------------------

    def _call_llm(self, prompt: str, system: str = "", tools: Iterable[dict] | None = None,
                  temperature: float = 0.2, max_tokens: int = 2048) -> str:
        """Tier-aware LLM invocation with automatic model fall-through."""
        for model in models_for_tier(self.model_tier):
            try:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system or self.default_system()},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if tools:
                    payload["tools"] = list(tools)
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=90,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except Exception as exc:  # noqa: BLE001 — model-level fall-through is intentional
                LOG.warning("tier %s model %s failed: %s", self.model_tier, model, exc)
                continue
        # Offline / no-key fallback: return a structured echo so downstream
        # agents can still make progress (used heavily in CI / unit tests).
        LOG.warning("all tier-%s models unavailable; returning offline stub", self.model_tier)
        return json.dumps({"offline": True, "agent": self.name, "prompt_excerpt": prompt[:200]})

    # -- subclass hooks -----------------------------------------------------

    def default_system(self) -> str:
        return (
            f"You are {self.name}, a Mythos-level autonomous security research agent. "
            "Reply ONLY with valid JSON describing your decisions and tool calls."
        )

    def act(self, context: dict[str, Any]) -> AgentMessage:  # pragma: no cover
        raise NotImplementedError
