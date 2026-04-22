"""
ARCHITECT — typed model-tier router (§8 of the Masterplan).

Routes every LLM call to the cheapest model that can do the job, while
keeping a per-task fallback chain.  All calls go through OpenRouter unless
the task is mapped to the local ``vLLM`` endpoint.

Environment:

    OPENROUTER_API_KEY          — required for tiers 1-4
    OPENROUTER_BASE_URL         — defaults to https://openrouter.ai/api/v1
    LOCAL_VLLM_BASE_URL         — defaults to http://localhost:8000/v1
    ARCHITECT_DEFAULT_MAX_TOKENS — default 4096
    ARCHITECT_HARD_BUDGET_USD   — abort the day if this is exceeded
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

LOG = logging.getLogger("architect.model_router")

# ── Tier table (Masterplan §8.1) ────────────────────────────────────────────
TIER1_PRIMARY    = "deepseek/deepseek-chat-v3"
TIER2_PRIMARY    = "minimax/minimax-m2.5"
TIER3_PRIMARY    = "qwen/qwen3-235b-a22b"
TIER4_PRIMARY    = "anthropic/claude-sonnet-4-6"
TIER5_LOCAL      = "local/deepseek-r1-32b-awq"

# Per-task → preferred model, with overflow chain.
TASK_ROUTES: dict[str, list[str]] = {
    "static_analysis":        [TIER1_PRIMARY, TIER2_PRIMARY],
    "patch_generation":       [TIER1_PRIMARY, TIER2_PRIMARY],
    "recon":                  [TIER1_PRIMARY, TIER5_LOCAL],
    "report_drafting":        [TIER1_PRIMARY, TIER2_PRIMARY],
    "long_context_analysis":  [TIER2_PRIMARY, TIER1_PRIMARY],
    "exploit_reasoning":      [TIER2_PRIMARY, TIER4_PRIMARY],
    "adversarial_review_a":   [TIER1_PRIMARY],
    "adversarial_review_b":   [TIER2_PRIMARY],
    "adversarial_review_c":   [TIER3_PRIMARY],
    "critical_cve_draft":     [TIER4_PRIMARY, TIER2_PRIMARY],
    "bulk_triage":            [TIER5_LOCAL, TIER1_PRIMARY],
}

# Cost table ($/M tokens) used by the soft budget guardrail.
COST_PER_MTOKEN: dict[str, float] = {
    TIER1_PRIMARY: 0.27,
    TIER2_PRIMARY: 0.55,
    TIER3_PRIMARY: 0.90,
    TIER4_PRIMARY: 3.00,
    TIER5_LOCAL:   0.0,
}


@dataclass
class RouteDecision:
    task: str
    model: str
    reason: str
    fallback_chain: list[str]
    tier: int

    def to_json(self) -> str:
        return json.dumps(self.__dict__)


@dataclass
class _BudgetState:
    spent_usd: float = 0.0
    started_at: float = field(default_factory=time.time)
    hard_cap_usd: float = float(os.getenv("ARCHITECT_HARD_BUDGET_USD", "10.0"))


_BUDGET = _BudgetState()


def reset_budget(hard_cap_usd: float | None = None) -> None:
    global _BUDGET
    _BUDGET = _BudgetState(hard_cap_usd=hard_cap_usd or _BUDGET.hard_cap_usd)


def budget_status() -> dict[str, Any]:
    return {
        "spent_usd": round(_BUDGET.spent_usd, 4),
        "hard_cap_usd": _BUDGET.hard_cap_usd,
        "remaining_usd": round(_BUDGET.hard_cap_usd - _BUDGET.spent_usd, 4),
        "uptime_s": int(time.time() - _BUDGET.started_at),
    }


def _tier_of(model: str) -> int:
    return {
        TIER1_PRIMARY: 1, TIER2_PRIMARY: 2, TIER3_PRIMARY: 3,
        TIER4_PRIMARY: 4, TIER5_LOCAL: 5,
    }.get(model, 1)


def route(task: str, *, prefer: str | None = None) -> RouteDecision:
    """Pick the right model for a task. Honors the hard budget cap."""
    chain = TASK_ROUTES.get(task, [TIER1_PRIMARY])
    if prefer and prefer in chain:
        chain = [prefer] + [m for m in chain if m != prefer]
    chosen = chain[0]
    if _BUDGET.spent_usd >= _BUDGET.hard_cap_usd and chosen != TIER5_LOCAL:
        LOG.warning("Hard budget exceeded — falling back to local tier 5")
        chosen = TIER5_LOCAL
        reason = "budget-exceeded → local"
    elif prefer:
        reason = f"caller-preferred:{prefer}"
    else:
        reason = f"default-tier{_tier_of(chosen)}"
    return RouteDecision(task=task, model=chosen, reason=reason,
                         fallback_chain=chain, tier=_tier_of(chosen))


def record_usage(model: str, tokens: int) -> float:
    cost = (tokens / 1_000_000) * COST_PER_MTOKEN.get(model, 0.27)
    _BUDGET.spent_usd += cost
    return cost


def all_routes() -> dict[str, list[str]]:
    return dict(TASK_ROUTES)
