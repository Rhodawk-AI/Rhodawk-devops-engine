"""
Rhodawk AI — The Model Squad
============================
Single source of truth for the five LLM roles in the system, mapped to
DigitalOcean Serverless Inference IDs (PRIMARY brain) with OpenRouter
IDs held as a graceful FALLBACK.

The squad (operator-facing names → role keys → model IDs)

    1. The Hands       (EXECUTION)  llama3.3-70b-instruct
    2. The Brain       (HERMES)     deepseek-r1-distill-llama-70b
    3. The Reader      (RECON)      kimi-k2.5
    4. The Screener    (TRIAGE)     qwen3-32b
    5. The Safety Net  (FALLBACK)   claude-4.6-sonnet  /  minimax-m2.5

DigitalOcean Serverless Inference (PRIMARY)
-------------------------------------------
* Base URL  : https://inference.do-ai.run/v1   (override with DO_INFERENCE_BASE_URL)
* Auth      : Authorization: Bearer ${DO_INFERENCE_API_KEY}
* Endpoint  : POST /chat/completions   (OpenAI-compatible)
* Hosted    : llama3.3-70b-instruct, deepseek-r1-distill-llama-70b,
              qwen3-32b-instruct + others — see DO catalog at
              https://docs.digitalocean.com/products/genai/serverless-inference/
* Not hosted: kimi-k2.5, claude-4.6-sonnet, minimax-m2.5 — these
              automatically resolve to OpenRouter when DO is unable to
              serve them.

OpenRouter (FALLBACK)
---------------------
* Base URL  : https://openrouter.ai/api/v1
* Auth      : Authorization: Bearer ${OPENROUTER_API_KEY}
* Used      : as a graceful overflow lane and as the only path for the
              three emergency-tier models (kimi / claude / minimax).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# ────────────────────────────────────────────────────────────────────────────
# Provider endpoints
# ────────────────────────────────────────────────────────────────────────────

DO_INFERENCE_API_KEY = os.getenv("DO_INFERENCE_API_KEY", "") or os.getenv(
    "DIGITALOCEAN_INFERENCE_KEY", ""
)
DO_INFERENCE_BASE_URL = os.getenv(
    "DO_INFERENCE_BASE_URL", "https://inference.do-ai.run/v1"
).rstrip("/")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
).rstrip("/")


# ────────────────────────────────────────────────────────────────────────────
# Role → model registry
# ────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SquadModel:
    """One role in the model squad."""

    role: str            # canonical role key
    nickname: str        # human-facing name
    do_id: str           # DigitalOcean Serverless Inference model id
    or_id: str           # OpenRouter fallback model id
    on_do: bool          # True if DO actually hosts this model
    purpose: str         # one-line description


_DEFAULT_SQUAD: tuple[SquadModel, ...] = (
    SquadModel(
        role="EXECUTION",
        nickname="The Hands",
        do_id=os.getenv("EXECUTION_MODEL", "llama3.3-70b-instruct"),
        # Playbook §3 — Replace the hardcoded llama3.3-70b-instruct OR
        # fallback with kimi-k2.5 so secure JSON tool-calling continues
        # to work when the DO primary fails.
        or_id=os.getenv(
            "EXECUTION_MODEL_OR",
            "moonshotai/kimi-k2.5",
        ),
        on_do=True,
        purpose="primary executor — code edits, fix generation, tool calls",
    ),
    SquadModel(
        role="HERMES",
        nickname="The Brain",
        do_id=os.getenv("HERMES_MODEL", "deepseek-r1-distill-llama-70b"),
        or_id=os.getenv(
            "HERMES_MODEL_OR",
            "deepseek/deepseek-r1-distill-llama-70b",
        ),
        on_do=True,
        purpose="reasoning + Godmode meta-learning",
    ),
    SquadModel(
        role="RECON",
        nickname="The Reader",
        # DO does not host Kimi today; the router will auto-fall over to OR.
        do_id=os.getenv("RECON_MODEL", "kimi-k2.5"),
        or_id=os.getenv("RECON_MODEL_OR", "moonshotai/kimi-k2.5"),
        on_do=False,
        purpose="massive-context ingestion (whole-repo + bug-bounty pages)",
    ),
    SquadModel(
        role="TRIAGE",
        nickname="The Screener",
        do_id=os.getenv("TRIAGE_MODEL", "qwen3-32b"),
        or_id=os.getenv("TRIAGE_MODEL_OR", "qwen/qwen3-32b"),
        on_do=True,
        purpose="fast cheap filtering — bulk triage, scope parsing",
    ),
    SquadModel(
        role="FALLBACK",
        nickname="The Safety Net",
        # The two emergency models live exclusively on OpenRouter.
        do_id=os.getenv("FALLBACK_MODEL", "claude-4.6-sonnet"),
        or_id=os.getenv("FALLBACK_MODEL_OR", "anthropic/claude-sonnet-4.6"),
        on_do=False,
        purpose="emergency safety net — only when open-source models fail",
    ),
    SquadModel(
        role="FALLBACK_ALT",
        nickname="The Safety Net (alt)",
        do_id=os.getenv("FALLBACK_MODEL_ALT", "minimax-m2.5"),
        or_id=os.getenv("FALLBACK_MODEL_ALT_OR", "minimax/minimax-m2.5"),
        on_do=False,
        purpose="emergency safety net (second choice)",
    ),
)


_BY_ROLE: dict[str, SquadModel] = {m.role: m for m in _DEFAULT_SQUAD}


def get(role: str) -> SquadModel:
    """Return the squad entry for a role, defaulting to EXECUTION."""
    return _BY_ROLE.get(role.upper(), _BY_ROLE["EXECUTION"])


def all_models() -> tuple[SquadModel, ...]:
    return _DEFAULT_SQUAD


# Convenience constants (the first three are the only ones DO actually
# hosts — every other consumer can safely default to one of these).
EXECUTION_MODEL_DO = _BY_ROLE["EXECUTION"].do_id
HERMES_MODEL_DO    = _BY_ROLE["HERMES"].do_id
TRIAGE_MODEL_DO    = _BY_ROLE["TRIAGE"].do_id

EXECUTION_MODEL_OR = _BY_ROLE["EXECUTION"].or_id
HERMES_MODEL_OR    = _BY_ROLE["HERMES"].or_id
TRIAGE_MODEL_OR    = _BY_ROLE["TRIAGE"].or_id


def primary_provider() -> str:
    """Return the name of the provider currently configured as primary.
    Always 'DigitalOcean' if DO_INFERENCE_API_KEY is set, else 'OpenRouter',
    else 'none'."""
    if DO_INFERENCE_API_KEY:
        return "DigitalOcean"
    if OPENROUTER_API_KEY:
        return "OpenRouter"
    return "none"


def describe() -> str:
    """Human-readable squad summary for log lines / status panels."""
    lines = [
        f"PRIMARY provider : {primary_provider()}",
        f"DO base URL      : {DO_INFERENCE_BASE_URL}",
        f"OR base URL      : {OPENROUTER_BASE_URL}",
        "Model squad:",
    ]
    for m in _DEFAULT_SQUAD:
        provider = "DO" if m.on_do and DO_INFERENCE_API_KEY else "OR"
        model_id = m.do_id if provider == "DO" else m.or_id
        lines.append(f"  {m.role:<13} {m.nickname:<22} → {provider} :: {model_id}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(describe())
