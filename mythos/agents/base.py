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

# Tier IDs use DigitalOcean Serverless Inference catalog names (PRIMARY).
# When the request is routed to OpenRouter the model id is rewritten via
# _OR_FALLBACK_FOR below.
_DEFAULT_MODELS = {
    "tier1": [
        os.getenv("MYTHOS_TIER1_PRIMARY",  "deepseek-r1-distill-llama-70b"),
        os.getenv("MYTHOS_TIER1_FALLBACK", "llama-3.3-70b-instruct"),
        "qwen3-32b",
    ],
    "tier2": [
        os.getenv("MYTHOS_TIER2_PRIMARY",  "llama-3.3-70b-instruct"),
        os.getenv("MYTHOS_TIER2_FALLBACK", "qwen3-32b"),
    ],
    "tier3": [
        "llama-3.3-70b-instruct",
        "deepseek-r1-distill-llama-70b",
        "qwen3-32b",
    ],
}

# Map DO catalog ids to their OpenRouter equivalents for the fallback path.
_OR_FALLBACK_FOR: dict[str, str] = {
    "deepseek-r1-distill-llama-70b": "deepseek/deepseek-r1-distill-llama-70b",
    "llama-3.3-70b-instruct":        "meta-llama/llama-3.3-70b-instruct",
    "qwen3-32b":                     "qwen/qwen3-32b",
    # Emergency-tier (OR-only) models, used when an operator overrides MYTHOS_*:
    "claude-4.6-sonnet":             "anthropic/claude-sonnet-4.6",
    "minimax-m2.5":                  "minimax/minimax-m2.5",
    "kimi-k2.5":                     "moonshotai/kimi-k2.5",
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
    """Concrete agents subclass this and implement ``act()``.

    DigitalOcean Serverless Inference is the PRIMARY provider; OpenRouter is
    the FALLBACK. The constructor still accepts ``openrouter_key`` for
    backwards compatibility with old callers, but it is now used only on the
    fallback leg.
    """

    name: str = "agent"
    model_tier: str = "tier1"

    def __init__(self, openrouter_key: str | None = None, base_url: str | None = None):
        # DO PRIMARY
        self.do_key = os.getenv("DO_INFERENCE_API_KEY", "") or os.getenv(
            "DIGITALOCEAN_INFERENCE_KEY", "")
        self.do_base = os.getenv(
            "DO_INFERENCE_BASE_URL", "https://inference.do-ai.run/v1").rstrip("/")
        # OR FALLBACK
        self.openrouter_key = openrouter_key or os.getenv("OPENROUTER_API_KEY", "")
        self.or_base = (base_url or os.getenv(
            "MYTHOS_LLM_BASE", "https://openrouter.ai/api/v1")).rstrip("/")

    # -- tool-calling -------------------------------------------------------

    def _post(self, base_url: str, api_key: str, model: str, system: str,
              prompt: str, tools, temperature: float, max_tokens: int) -> str:
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
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=90,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_llm(self, prompt: str, system: str = "", tools: Iterable[dict] | None = None,
                  temperature: float = 0.2, max_tokens: int = 2048) -> str:
        """Tier-aware LLM invocation with DO-primary, OR-fallback failover.

        For each model in the tier list:
          1. Try DigitalOcean (DO_INFERENCE_API_KEY) with the catalog id.
          2. On any failure, try OpenRouter (OPENROUTER_API_KEY) with the
             OR-shaped id from _OR_FALLBACK_FOR.
        """
        for model in models_for_tier(self.model_tier):
            # 1) DO PRIMARY
            if self.do_key:
                try:
                    return self._post(self.do_base, self.do_key, model,
                                      system, prompt, tools, temperature, max_tokens)
                except Exception as exc:  # noqa: BLE001
                    LOG.warning("tier %s DO %s failed: %s", self.model_tier, model, exc)
            # 2) OR FALLBACK
            if self.openrouter_key:
                or_model = _OR_FALLBACK_FOR.get(model, model)
                try:
                    return self._post(self.or_base, self.openrouter_key, or_model,
                                      system, prompt, tools, temperature, max_tokens)
                except Exception as exc:  # noqa: BLE001
                    LOG.warning("tier %s OR %s failed: %s", self.model_tier, or_model, exc)
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
