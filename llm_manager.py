"""
Rhodawk AI — Multi-Tier LLM Manager
====================================
Component-specific LLM routing with built-in fallbacks for the
Embodied OS architecture.

Primary infrastructure  : DigitalOcean Serverless Inference
                          (https://inference.do-ai.run/v1)
Fallback infrastructure : NVIDIA NIM
                          (https://integrate.api.nvidia.com/v1)

Both providers expose an OpenAI-compatible chat-completions endpoint,
so a single `openai.OpenAI` client is dynamically reconfigured at call
time — only `base_url` and `api_key` change between providers.

Routing dictionary (per Embodied OS component)
----------------------------------------------
    core_reasoning : DeepSeek R1 (DO)            -> DeepSeek R1 (NVIDIA)
    log_analyzer   : Llama 3 8B Instruct (DO)    -> Llama 3.1 8B Instruct (NVIDIA)
    fuzz_monitor   : Llama 3 8B Instruct (DO)    -> Llama 3.1 8B Instruct (NVIDIA)

Model IDs are sourced from the live provider catalogues
(verified against the DO Gradient Serverless Inference docs and the
NVIDIA NIM build.nvidia.com catalogue at integration time).

Environment variables (loaded from `.env`)
------------------------------------------
    DO_API_KEY           — DigitalOcean Serverless Inference key (primary)
    NVIDIA_API_KEY       — NVIDIA NIM key (fallback)
    DO_BASE_URL          — optional override (default DO endpoint)
    NVIDIA_BASE_URL      — optional override (default NVIDIA endpoint)
    LLM_MANAGER_DEBUG    — set to "1" for verbose stderr routing logs

Public surface
--------------
    LLMManager().chat(component, messages, **kwargs) -> dict
    LLMManager().chat_text(component, messages, **kwargs) -> str

The class is thread-safe: each call constructs its own short-lived
`openai.OpenAI` client, so two threads (e.g. fuzz_monitor + log_analyzer)
can route through different providers concurrently without sharing
mutable client state.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Iterable

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:  # noqa: BLE001 — dotenv is optional
    pass

LOG = logging.getLogger("rhodawk.llm_manager")

DEBUG = os.getenv("LLM_MANAGER_DEBUG", "0") == "1"


def _dbg(msg: str) -> None:
    if DEBUG:
        print(f"[llm_manager] {msg}", file=sys.stderr, flush=True)


# ── Provider endpoints ─────────────────────────────────────────────────────
DO_BASE_URL = os.getenv(
    "DO_BASE_URL", "https://inference.do-ai.run/v1"
).rstrip("/")
NVIDIA_BASE_URL = os.getenv(
    "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"
).rstrip("/")

# The user's spec uses DO_API_KEY / NVIDIA_API_KEY as the canonical names,
# but we accept the older DO_INFERENCE_API_KEY for back-compat with
# `model_squad.py` so existing deployments don't break.
DO_API_KEY = (
    os.getenv("DO_API_KEY")
    or os.getenv("DO_INFERENCE_API_KEY")
    or os.getenv("DIGITALOCEAN_INFERENCE_KEY")
    or ""
)
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "") or os.getenv("NIM_API_KEY", "")


# ── Component routing table ────────────────────────────────────────────────
@dataclass(frozen=True)
class ProviderModel:
    provider: str         # "digitalocean" | "nvidia"
    base_url: str
    api_key: str
    model: str

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


@dataclass(frozen=True)
class ComponentRoute:
    component: str
    primary: ProviderModel
    fallback: ProviderModel
    purpose: str


def _build_routes() -> dict[str, ComponentRoute]:
    """Resolve the per-component routing table from .env at construction time."""
    do_reasoning = os.getenv(
        "DO_REASONING_MODEL", "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"
    )
    do_fast = os.getenv("DO_FAST_MODEL", "llama3-8b-instruct")
    nv_reasoning = os.getenv("NVIDIA_REASONING_MODEL", "deepseek-ai/deepseek-r1")
    nv_fast = os.getenv("NVIDIA_FAST_MODEL", "meta/llama-3.1-8b-instruct")

    def do(model: str) -> ProviderModel:
        return ProviderModel("digitalocean", DO_BASE_URL, DO_API_KEY, model)

    def nv(model: str) -> ProviderModel:
        return ProviderModel("nvidia", NVIDIA_BASE_URL, NVIDIA_API_KEY, model)

    return {
        "core_reasoning": ComponentRoute(
            component="core_reasoning",
            primary=do(do_reasoning),
            fallback=nv(nv_reasoning),
            purpose="primary reasoning brain — Hermes / Godmode meta-learning",
        ),
        "log_analyzer": ComponentRoute(
            component="log_analyzer",
            primary=do(do_fast),
            fallback=nv(nv_fast),
            purpose="fast log triage and structured-event extraction",
        ),
        "fuzz_monitor": ComponentRoute(
            component="fuzz_monitor",
            primary=do(do_fast),
            fallback=nv(nv_fast),
            purpose="fuzz harness watchdog and crash-summary generator",
        ),
    }


# ── Errors ─────────────────────────────────────────────────────────────────
class LLMUnavailableError(RuntimeError):
    """Neither the primary nor the fallback provider could serve the call."""


class UnknownComponentError(KeyError):
    """The requested component has no entry in the routing table."""


# ── Manager ────────────────────────────────────────────────────────────────
class LLMManager:
    """
    Component-aware LLM router with primary→fallback failover.

    Usage:
        mgr = LLMManager()
        out = mgr.chat_text("core_reasoning", [{"role": "user", "content": "hi"}])
    """

    # 429 backoff windows (seconds) tried inside one provider before
    # giving up and falling over to the next.
    _RATE_LIMIT_BACKOFF: tuple[int, ...] = (3, 8, 20)

    def __init__(self, routes: dict[str, ComponentRoute] | None = None) -> None:
        self._routes: dict[str, ComponentRoute] = routes or _build_routes()
        # Guard concurrent route mutation (`add_component`, hot-reload).
        # The lock is INTENTIONALLY only used for table-level reads/writes,
        # never held during the network call — a slow upstream cannot
        # block other components from looking up their own route.
        self._table_lock = threading.RLock()

    # ── Public API ────────────────────────────────────────────────────────
    @property
    def components(self) -> tuple[str, ...]:
        with self._table_lock:
            return tuple(self._routes.keys())

    def get_route(self, component: str) -> ComponentRoute:
        with self._table_lock:
            try:
                return self._routes[component]
            except KeyError as exc:
                raise UnknownComponentError(
                    f"unknown component {component!r} — known: {list(self._routes)}"
                ) from exc

    def add_component(self, route: ComponentRoute) -> None:
        with self._table_lock:
            self._routes[route.component] = route

    def chat(
        self,
        component: str,
        messages: list[dict[str, Any]],
        *,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """
        Run a chat completion for `component`. Returns the raw provider
        response dict (OpenAI-compatible).

        Failover order:
          1. component.primary  (DigitalOcean)
          2. component.fallback (NVIDIA NIM)

        Raises `LLMUnavailableError` if both providers are unconfigured
        or both fail.
        """
        route = self.get_route(component)

        last_error: Exception | None = None
        for tier_name, target in (("PRIMARY", route.primary),
                                  ("FALLBACK", route.fallback)):
            if not target.configured:
                _dbg(f"{component} :: {tier_name} {target.provider} skipped — no API key")
                continue
            try:
                resp = self._call_provider(
                    component=component,
                    target=target,
                    messages=messages,
                    json_mode=json_mode,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
                if resp is not None:
                    _dbg(f"{component} :: served by {tier_name} {target.provider} :: {target.model}")
                    return resp
            except Exception as exc:  # noqa: BLE001 — fall over to next tier
                last_error = exc
                _dbg(f"{component} :: {tier_name} {target.provider} failed — {exc}")

        raise LLMUnavailableError(
            f"component={component!r}: primary and fallback both failed "
            f"(last error: {last_error!r})"
        )

    def chat_text(
        self,
        component: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> str:
        """Return just the assistant's text content."""
        raw = self.chat(component, messages, **kwargs)
        try:
            return raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMUnavailableError(f"unexpected response shape: {e}") from e

    # ── Internals ─────────────────────────────────────────────────────────
    def _call_provider(
        self,
        *,
        component: str,
        target: ProviderModel,
        messages: list[dict[str, Any]],
        json_mode: bool,
        temperature: float,
        max_tokens: int,
        timeout: int,
    ) -> dict[str, Any] | None:
        """
        Execute one provider call with rate-limit backoff. Returns the
        decoded response dict or None on a non-recoverable provider error.
        """
        # Late import so the dependency only matters when the manager is
        # actually used. `openai>=1.0` is required.
        try:
            from openai import OpenAI  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise LLMUnavailableError(
                "openai SDK >=1.0 not installed — `pip install openai`"
            ) from exc

        # Per-call client. The OpenAI SDK is not strictly thread-safe for
        # concurrent reuse with mutated state, and constructing one is
        # cheap, so we instantiate fresh on each call. This is what makes
        # the manager safe to invoke from multiple Embodied OS components
        # at once (see thread-safety note in module docstring).
        client = OpenAI(
            base_url=target.base_url,
            api_key=target.api_key,
            timeout=timeout,
        )

        request_kwargs: dict[str, Any] = {
            "model": target.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            request_kwargs["response_format"] = {"type": "json_object"}

        for attempt, wait in enumerate((0,) + self._RATE_LIMIT_BACKOFF):
            if wait:
                _dbg(f"{component} :: {target.provider} 429 backoff {wait}s "
                     f"(attempt {attempt})")
                time.sleep(wait)
            try:
                completion = client.chat.completions.create(**request_kwargs)
                # Normalise to a plain dict regardless of SDK return type.
                if hasattr(completion, "model_dump"):
                    return completion.model_dump()
                if isinstance(completion, dict):
                    return completion
                return dict(completion)  # last-ditch
            except Exception as exc:  # noqa: BLE001
                # Detect 429s without importing the openai exception
                # hierarchy directly — the classes have moved between
                # SDK versions and we don't want a hard dependency.
                msg = str(exc).lower()
                status = getattr(exc, "status_code", None) or getattr(
                    exc, "http_status", None
                )
                if status == 429 or "rate limit" in msg or "429" in msg:
                    continue  # retry with the next backoff window
                _dbg(f"{component} :: {target.provider} hard error — {exc!r}")
                return None
        _dbg(f"{component} :: {target.provider} exhausted {len(self._RATE_LIMIT_BACKOFF)} retries")
        return None

    # ── Diagnostics ───────────────────────────────────────────────────────
    def describe(self) -> str:
        lines = ["LLMManager routing table:",
                 f"  DO key configured     : {bool(DO_API_KEY)}",
                 f"  NVIDIA key configured : {bool(NVIDIA_API_KEY)}",
                 f"  DO base URL           : {DO_BASE_URL}",
                 f"  NVIDIA base URL       : {NVIDIA_BASE_URL}",
                 ""]
        for c in self.components:
            r = self.get_route(c)
            lines.append(f"  {r.component}")
            lines.append(f"    primary  → {r.primary.provider:<12} :: {r.primary.model}")
            lines.append(f"    fallback → {r.fallback.provider:<12} :: {r.fallback.model}")
            lines.append(f"    purpose  : {r.purpose}")
        return "\n".join(lines)


# ── Module-level singleton (lazy) ──────────────────────────────────────────
_DEFAULT_MANAGER: LLMManager | None = None
_DEFAULT_MANAGER_LOCK = threading.Lock()


def default_manager() -> LLMManager:
    """Return a process-wide LLMManager instance, constructing on first call.

    Double-checked locking prevents the race where two threads both see
    `_DEFAULT_MANAGER is None` and construct duplicate managers.
    """
    global _DEFAULT_MANAGER
    if _DEFAULT_MANAGER is None:
        with _DEFAULT_MANAGER_LOCK:
            if _DEFAULT_MANAGER is None:
                _DEFAULT_MANAGER = LLMManager()
    return _DEFAULT_MANAGER


def chat(component: str, messages: list[dict[str, Any]], **kwargs: Any) -> dict:
    """Module-level convenience: `llm_manager.chat("core_reasoning", msgs)`."""
    return default_manager().chat(component, messages, **kwargs)


def chat_text(component: str, messages: list[dict[str, Any]], **kwargs: Any) -> str:
    return default_manager().chat_text(component, messages, **kwargs)


# Component name aliases — accept underscore or hyphen variants so callers
# can use whichever feels natural in their module.
_COMPONENT_ALIASES: dict[str, str] = {
    "core-reasoning": "core_reasoning",
    "log-analyzer": "log_analyzer",
    "fuzz-monitor": "fuzz_monitor",
}


def normalize_component(name: str) -> str:
    return _COMPONENT_ALIASES.get(name, name)


def known_components() -> Iterable[str]:
    return default_manager().components


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    print(default_manager().describe())
