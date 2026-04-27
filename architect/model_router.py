"""
ARCHITECT — typed model-tier router (§8 of the Masterplan, v2 — Apr 2026).

Routes every LLM call to the cheapest model that can do the job, while
keeping a per-task fallback chain.  All calls go through OpenRouter unless
the task is mapped to the local ``vLLM`` endpoint.

Tier table (Masterplan §1.1, confirmed April 2026):

    T1-fast  MiniMax M2.5-highspeed   — recon, triage, bulk scan
    T1-deep  DeepSeek V3              — static analysis, patch generation
    T2       Qwen3-235B-A22B          — exploit reasoning, attack graphs
    T3       MiniMax M2.5             — long-context repo analysis
    T4       Claude Sonnet 4.6        — P1/P2 final report polish
    T5       DeepSeek-R1-32B-AWQ      — local Kaggle GPU bulk triage

Environment:

    OPENROUTER_API_KEY              — required for tiers 1-4
    OPENROUTER_BASE_URL             — defaults to https://openrouter.ai/api/v1
    LOCAL_VLLM_BASE_URL             — defaults to http://localhost:8000/v1
    ARCHITECT_DEFAULT_MAX_TOKENS    — default 4096
    ARCHITECT_HARD_BUDGET_USD       — abort the day if this is exceeded
    TIER1_PRIMARY_MODEL / TIER1_DEEP_MODEL / TIER2_PRIMARY_MODEL
    TIER3_PRIMARY_MODEL / TIER4_PRIMARY_MODEL — env overrides
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

LOG = logging.getLogger("architect.model_router")

# ── Tier table (Masterplan §1.1) ────────────────────────────────────────────
# Defaults follow the Model Squad: cheap DO catalog ids first, OR-only
# emergency models on the higher tiers. Override any of these via env.
TIER1_PRIMARY = os.getenv("TIER1_PRIMARY_MODEL", "qwen3-32b")                  # TRIAGE
TIER1_DEEP    = os.getenv("TIER1_DEEP_MODEL",    "llama3.3-70b-instruct")     # EXECUTION
TIER2_PRIMARY = os.getenv("TIER2_PRIMARY_MODEL", "deepseek-r1-distill-llama-70b")  # HERMES
TIER3_PRIMARY = os.getenv("TIER3_PRIMARY_MODEL", "kimi-k2.5")                  # RECON (OR-only)
TIER4_PRIMARY = os.getenv("TIER4_PRIMARY_MODEL", "claude-4.6-sonnet")          # FALLBACK (OR-only)
TIER5_LOCAL   = os.getenv("TIER5_LOCAL_MODEL",   "minimax-m2.5")               # FALLBACK_ALT (OR-only)

# Playbook §3 — Secure JSON tool-calling fallback. When the primary
# DO/OpenRouter provider fails on a code-heavy task, fall over to
# kimi-k2.5 (TIER3_PRIMARY) instead of the previously hardcoded
# llama3.3-70b-instruct, which is unreliable for strict JSON tool calls.
JSON_TOOL_CALL_FALLBACK = TIER3_PRIMARY

# Per-task → preferred model, with overflow chain.
TASK_ROUTES: dict[str, list[str]] = {
    # Lightweight bulk work — T1-fast first, T5 local fallback.
    "recon":                  [TIER1_PRIMARY, TIER5_LOCAL],
    "bulk_triage":            [TIER5_LOCAL, TIER1_PRIMARY],
    "scope_parse":            [TIER1_PRIMARY, TIER5_LOCAL],
    # Code-heavy reasoning — DeepSeek V3 deep tier, then kimi for secure
    # JSON tool-calling instead of the old llama-fallback (Playbook §3).
    "static_analysis":        [TIER1_DEEP, JSON_TOOL_CALL_FALLBACK, TIER2_PRIMARY],
    "patch_generation":       [TIER1_DEEP, JSON_TOOL_CALL_FALLBACK],
    # Logic chains and exploit graphs — Qwen3 MoE.
    "exploit_reasoning":      [TIER2_PRIMARY, JSON_TOOL_CALL_FALLBACK, TIER4_PRIMARY],
    "chain_synthesis":        [TIER2_PRIMARY, JSON_TOOL_CALL_FALLBACK],
    # Long-context whole-repo work.
    "long_context_analysis":  [TIER3_PRIMARY, TIER1_PRIMARY],
    # ACTS 3-model consensus — distinct providers on purpose.
    "adversarial_review_a":   [TIER1_PRIMARY],
    "adversarial_review_b":   [TIER1_DEEP],
    "adversarial_review_c":   [TIER2_PRIMARY],
    # Final-mile report polish — only model worth paying T4 for.
    "report_drafting":        [TIER1_DEEP, JSON_TOOL_CALL_FALLBACK],
    "critical_cve_draft":     [TIER4_PRIMARY, TIER2_PRIMARY],
}

# Cost table ($/M output tokens) used by the soft budget guardrail.
COST_PER_MTOKEN: dict[str, float] = {
    TIER1_PRIMARY: 0.10,
    TIER1_DEEP:    0.28,
    TIER2_PRIMARY: 0.60,
    TIER3_PRIMARY: 0.55,
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
        TIER1_PRIMARY: 1, TIER1_DEEP: 1,
        TIER2_PRIMARY: 2, TIER3_PRIMARY: 3,
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


# ── AutoTune EMA — exponential-moving-average of ACTS scores per model ──────
# Updates TASK_ROUTES in-process to promote higher-scoring models over time.
# α = 0.15 (slow EMA, resists noise from single bad runs).
# Caller should invoke `autotune_record(task, model, acts_score)` after every
# scored consensus race. Call `autotune_promote()` periodically (e.g. hourly)
# to apply EMA-derived ordering to TASK_ROUTES.

import threading as _threading
from collections import defaultdict as _defaultdict

_EMA_ALPHA: float = float(os.getenv("AUTOTUNE_EMA_ALPHA", "0.15"))
_EMA_MIN_SAMPLES: int = int(os.getenv("AUTOTUNE_EMA_MIN_SAMPLES", "5"))
_ema_scores: dict[str, dict[str, float]] = _defaultdict(dict)   # task → model → ema
_ema_counts: dict[str, dict[str, int]]  = _defaultdict(lambda: _defaultdict(int))
_ema_lock = _threading.Lock()


def autotune_record(task: str, model: str, acts_score: float) -> None:
    """
    Update the EMA for (task, model) with a new ACTS score.

    Called automatically after every ``race()`` that produces a scored winner.
    """
    with _ema_lock:
        prev = _ema_scores[task].get(model, acts_score)
        _ema_scores[task][model] = _EMA_ALPHA * acts_score + (1.0 - _EMA_ALPHA) * prev
        _ema_counts[task][model] += 1
        LOG.debug(
            "AutoTune EMA: task=%s model=%s acts=%.1f ema=%.1f (n=%d)",
            task, model, acts_score,
            _ema_scores[task][model],
            _ema_counts[task][model],
        )


def autotune_promote() -> dict[str, list[str]]:
    """
    Re-order each task's model chain by descending EMA score.

    Only models that have at least ``_EMA_MIN_SAMPLES`` samples are eligible
    for promotion.  Under-sampled models stay in their original slot.
    Returns the updated TASK_ROUTES.
    """
    with _ema_lock:
        for task, chain in list(TASK_ROUTES.items()):
            task_scores = _ema_scores.get(task, {})
            task_counts = _ema_counts.get(task, {})
            mature = {m: s for m, s in task_scores.items()
                      if task_counts.get(m, 0) >= _EMA_MIN_SAMPLES and m in chain}
            if not mature:
                continue
            unsorted = [m for m in chain if m not in mature]
            promoted = sorted(mature, key=lambda m: mature[m], reverse=True)
            TASK_ROUTES[task] = promoted + unsorted
            LOG.info("AutoTune promoted task=%s order=%s", task, TASK_ROUTES[task])
    return dict(TASK_ROUTES)


def autotune_status() -> dict[str, Any]:
    """Return current EMA scores and sample counts for all (task, model) pairs."""
    with _ema_lock:
        return {
            "alpha": _EMA_ALPHA,
            "min_samples": _EMA_MIN_SAMPLES,
            "ema_scores": {t: dict(m) for t, m in _ema_scores.items()},
            "ema_counts": {t: dict(m) for t, m in _ema_counts.items()},
        }


# ── Skill-augmented context injection (Masterplan §1.2) ─────────────────────
def build_skill_system_prompt(
    profile: dict[str, Any],
    *,
    max_skills: int = 3,
    base_directive: str | None = None,
    pin_skills: list[str] | None = None,
) -> str:
    """
    Materialise the matched skill bodies into a single system prompt that
    can be prepended to any LLM call.  Pure helper — does not call the LLM.
    Returns "" if no skills match and no pinned skills are loadable.

    ``pin_skills`` — names of skills to *always* include regardless of
    profile match (e.g. ["vibe-coded-app-hunter"]).
    """
    try:
        from . import skill_registry  # local import: avoids cycles at module load
    except Exception as exc:  # noqa: BLE001
        LOG.warning("skill_registry unavailable: %s", exc)
        return ""

    matched = skill_registry.match(profile, top_k=max_skills)
    pinned: list = []
    if pin_skills:
        all_skills = skill_registry.load_all()
        wanted = {s.lower() for s in pin_skills}
        pinned = [s for s in all_skills if s.name.lower() in wanted]

    chosen = list({s.name: s for s in (pinned + matched)}.values())
    if not chosen:
        return ""
    parts: list[str] = []
    if base_directive:
        parts.append(base_directive.strip())
    parts.append(
        "You are a world-class security researcher. The following "
        "specialised skill briefings are loaded into your working memory. "
        "Apply them precisely; cite the relevant skill name when you use it."
    )
    for s in chosen:
        parts.append(f"\n## SKILL: {s.name}  (domain={s.domain})\n{s.body.strip()}")
    return "\n\n".join(parts)


def call_with_skills(
    task: str,
    user_prompt: str,
    profile: dict[str, Any],
    *,
    max_skills: int = 4,
    extra_system: str | None = None,
    llm_call: "callable | None" = None,
    mode: str = "hunt",
    use_master_prompt: bool = True,
    record_rl: bool = True,
    pin_skills: list[str] | None = None,
) -> dict[str, Any]:
    """
    Convenience wrapper:
      1. Pick the model for ``task`` via :func:`route`.
      2. Build the Master Red-Team operator prompt + skill pack
         (``use_master_prompt=True``, default) OR a plain skill pack.
      3. Hand off to ``llm_call(model, messages)``.
      4. (Optional) record the trace into the RL feedback loop so the
         OpenClaw fleet can train the local Tier-5 LoRA.

    ``mode`` — one of "hunt" | "exploit" | "fix" | "report" | "triage"
              (passed through to ``master_redteam_prompt``).
    ``pin_skills`` — defaults to ``["vibe-coded-app-hunter"]`` so the
                     20-rule hit-list rides with every call.
    """
    decision = route(task)
    pin = pin_skills if pin_skills is not None else ["vibe-coded-app-hunter"]
    skill_pack = build_skill_system_prompt(
        profile, max_skills=max_skills, base_directive=extra_system,
        pin_skills=pin,
    )

    if use_master_prompt:
        try:
            from . import master_redteam_prompt
            system = master_redteam_prompt.build_master_prompt(
                profile, mode=mode, extra_skill_pack=skill_pack,
            )
        except Exception as exc:  # noqa: BLE001
            LOG.warning("master_redteam_prompt unavailable: %s", exc)
            system = skill_pack
    else:
        system = skill_pack

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_prompt})

    if llm_call is None:
        try:
            from hermes_orchestrator import _hermes_llm_call as _llm
            llm_call = lambda model, msgs: _llm(msgs, model=model)  # noqa: E731
        except Exception as exc:  # noqa: BLE001
            LOG.warning("no llm_call provided and hermes import failed: %s", exc)
            return {"decision": decision, "system": system,
                    "messages": messages, "response": None,
                    "error": "no_llm_call"}

    response: Any = None
    try:
        response = llm_call(decision.model, messages)
    except Exception as exc:  # noqa: BLE001
        LOG.warning("llm_call failed: %s", exc)

    if record_rl and response is not None:
        try:
            from . import rl_feedback_loop
            text = response if isinstance(response, str) else (
                (response.get("content") if isinstance(response, dict) else "")
                or ""
            )
            rl_feedback_loop.record(
                task=task, model=decision.model,
                prompt=user_prompt, response=str(text),
                profile=profile,
            )
        except Exception as exc:  # noqa: BLE001
            LOG.debug("rl_feedback_loop.record failed: %s", exc)

    return {"decision": decision, "system": system,
            "messages": messages, "response": response, "mode": mode}
