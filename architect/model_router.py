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

# Per-task → preferred model, with overflow chain.
TASK_ROUTES: dict[str, list[str]] = {
    # Lightweight bulk work — T1-fast first, T5 local fallback.
    "recon":                  [TIER1_PRIMARY, TIER5_LOCAL],
    "bulk_triage":            [TIER5_LOCAL, TIER1_PRIMARY],
    "scope_parse":            [TIER1_PRIMARY, TIER5_LOCAL],
    # Code-heavy reasoning — DeepSeek V3 deep tier.
    "static_analysis":        [TIER1_DEEP, TIER1_PRIMARY, TIER2_PRIMARY],
    "patch_generation":       [TIER1_DEEP, TIER1_PRIMARY],
    # Logic chains and exploit graphs — Qwen3 MoE.
    "exploit_reasoning":      [TIER2_PRIMARY, TIER1_DEEP, TIER4_PRIMARY],
    "chain_synthesis":        [TIER2_PRIMARY, TIER1_DEEP],
    # Long-context whole-repo work.
    "long_context_analysis":  [TIER3_PRIMARY, TIER1_PRIMARY],
    # ACTS 3-model consensus — distinct providers on purpose.
    "adversarial_review_a":   [TIER1_PRIMARY],
    "adversarial_review_b":   [TIER1_DEEP],
    "adversarial_review_c":   [TIER2_PRIMARY],
    # Final-mile report polish — only model worth paying T4 for.
    "report_drafting":        [TIER1_DEEP, TIER1_PRIMARY],
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
