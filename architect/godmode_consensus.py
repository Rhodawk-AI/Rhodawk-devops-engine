"""
GODMODE Consensus — multi-model parallel racing (G0DM0D3-inspired).

Fires the same prompt across 3-N model+style combos in parallel, scores
each response on a composite metric, and returns the winner along with
the full leaderboard.  Re-uses the existing model router so every call
honours the hard budget cap and falls back to T5-local when needed.

Composite score (0-100):
    correctness   × 0.30
    specificity   × 0.20
    repro_clarity × 0.20
    cvss_uplift   × 0.20
    novelty       × 0.10

The scorer is a deterministic feature-based heuristic so we never need an
extra model call to judge — but a custom scorer can be passed in.

Public API:
    race(prompt, *, profile, combos=None, scorer=None) -> RaceResult
"""

from __future__ import annotations

import concurrent.futures as _cf
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from . import master_redteam_prompt, model_router

LOG = logging.getLogger("architect.godmode_consensus")

# Default 5-combo race table — one per family, deliberately diverse.
DEFAULT_COMBOS: list[dict[str, str]] = [
    {"model": model_router.TIER1_PRIMARY, "mode": "hunt",   "label": "minimax-fast"},
    {"model": model_router.TIER1_DEEP,    "mode": "hunt",   "label": "deepseek-deep"},
    {"model": model_router.TIER2_PRIMARY, "mode": "exploit","label": "qwen-exploit"},
    {"model": model_router.TIER4_PRIMARY, "mode": "report", "label": "sonnet-report"},
    {"model": model_router.TIER5_LOCAL,   "mode": "triage", "label": "local-triage"},
]


@dataclass
class CandidateResult:
    label: str
    model: str
    mode: str
    response: str
    latency_s: float
    score: float = 0.0
    breakdown: dict[str, float] = field(default_factory=dict)
    error: str | None = None


@dataclass
class RaceResult:
    prompt: str
    winner: CandidateResult | None
    leaderboard: list[CandidateResult]
    started_at: float
    finished_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "winner": self.winner.label if self.winner else None,
            "winning_score": self.winner.score if self.winner else 0.0,
            "leaderboard": [
                {"label": c.label, "model": c.model, "mode": c.mode,
                 "score": round(c.score, 2),
                 "latency_s": round(c.latency_s, 2),
                 "breakdown": c.breakdown,
                 "error": c.error}
                for c in self.leaderboard
            ],
            "elapsed_s": round(self.finished_at - self.started_at, 2),
        }


# ── Default heuristic scorer ───────────────────────────────────────────────
_RE_CWE   = re.compile(r"\bCWE-\d+\b", re.IGNORECASE)
_RE_CVSS  = re.compile(r"CVSS[: ]+\d", re.IGNORECASE)
_RE_REPRO = re.compile(r"^\s*(?:\d+\.|step\s*\d|repro)", re.IGNORECASE | re.MULTILINE)
_RE_CODE  = re.compile(r"```|^\s{4}\S", re.MULTILINE)


def default_scorer(response: str) -> tuple[float, dict[str, float]]:
    """Pure-text heuristic — never calls an LLM."""
    if not response:
        return 0.0, {"correctness": 0.0, "specificity": 0.0,
                     "repro_clarity": 0.0, "cvss_uplift": 0.0,
                     "novelty": 0.0}
    txt = response.strip()
    n_chars = len(txt)
    n_lines = txt.count("\n") + 1

    # correctness ≈ length & structure
    correctness = min(100.0, (n_chars / 1500.0) * 80.0 + (20.0 if n_lines > 8 else 0.0))
    # specificity ≈ presence of CWE / CVSS / file paths / function names
    specificity = 0.0
    if _RE_CWE.search(txt):  specificity += 35
    if _RE_CVSS.search(txt): specificity += 25
    specificity += min(40.0, len(re.findall(r"[/\w.-]+\.(?:py|js|ts|c|cpp|go|rs|java|sol)\b", txt)) * 8)
    specificity = min(100.0, specificity)
    # repro clarity ≈ numbered steps + code blocks
    repro = min(100.0, len(_RE_REPRO.findall(txt)) * 12 + (40 if _RE_CODE.search(txt) else 0))
    # cvss uplift ≈ explicit P1/P2 wording
    cvss = 0.0
    for kw, w in (("P1", 50), ("P2", 35), ("P3", 15), ("RCE", 30),
                  ("auth bypass", 30), ("idor", 20), ("ssrf", 20),
                  ("sqli", 25), ("rce", 30)):
        if re.search(rf"\b{re.escape(kw)}\b", txt, re.IGNORECASE):
            cvss += w
    cvss = min(100.0, cvss)
    # novelty ≈ avoidance of generic phrasing
    boilerplate = ["it is important to note", "as an ai", "in conclusion",
                   "i cannot", "i am unable", "let me know"]
    novelty = 100.0 - 20.0 * sum(1 for b in boilerplate if b in txt.lower())
    novelty = max(0.0, novelty)

    composite = (correctness * 0.30 + specificity * 0.20 +
                 repro * 0.20 + cvss * 0.20 + novelty * 0.10)
    return round(composite, 2), {
        "correctness": round(correctness, 1),
        "specificity": round(specificity, 1),
        "repro_clarity": round(repro, 1),
        "cvss_uplift": round(cvss, 1),
        "novelty": round(novelty, 1),
    }


# ── LLM call adapter ───────────────────────────────────────────────────────
def _default_llm_call(model: str, messages: list[dict]) -> str:
    """Call the production Hermes LLM helper.  Returns the assistant text."""
    try:
        from hermes_orchestrator import _hermes_llm_call
        out = _hermes_llm_call(messages, model=model)
        if isinstance(out, dict):
            return str(out.get("content")
                       or (out.get("choices") or [{}])[0].get("message", {}).get("content")
                       or "")
        return str(out or "")
    except Exception as exc:  # noqa: BLE001
        LOG.warning("LLM call failed (model=%s): %s", model, exc)
        raise


# ── Public race entry point ────────────────────────────────────────────────
def race(
    user_prompt: str,
    *,
    profile: dict[str, Any] | None = None,
    combos: list[dict[str, str]] | None = None,
    scorer: Callable[[str], tuple[float, dict[str, float]]] | None = None,
    llm_call: Callable[[str, list[dict]], str] | None = None,
    timeout_s: float = 90.0,
) -> RaceResult:
    """
    Fan out ``user_prompt`` across ``combos`` (default 5), score each, return
    the winner + full leaderboard.
    """
    started = time.time()
    combos = combos or DEFAULT_COMBOS
    scorer = scorer or default_scorer
    llm_call = llm_call or _default_llm_call

    def _one(combo: dict[str, str]) -> CandidateResult:
        t0 = time.time()
        msgs = master_redteam_prompt.as_messages(
            user_prompt, profile, mode=combo.get("mode", "hunt"))
        try:
            text = llm_call(combo["model"], msgs)
        except Exception as exc:  # noqa: BLE001
            return CandidateResult(label=combo["label"], model=combo["model"],
                                   mode=combo["mode"], response="",
                                   latency_s=time.time() - t0, error=str(exc))
        score, breakdown = scorer(text)
        return CandidateResult(label=combo["label"], model=combo["model"],
                               mode=combo["mode"], response=text,
                               latency_s=time.time() - t0,
                               score=score, breakdown=breakdown)

    results: list[CandidateResult] = []
    with _cf.ThreadPoolExecutor(max_workers=len(combos)) as pool:
        futures = {pool.submit(_one, c): c for c in combos}
        for fut in _cf.as_completed(futures, timeout=timeout_s):
            try:
                results.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                c = futures[fut]
                results.append(CandidateResult(label=c["label"], model=c["model"],
                                               mode=c["mode"], response="",
                                               latency_s=0.0, error=str(exc)))

    results.sort(key=lambda r: r.score, reverse=True)
    winner = results[0] if results and results[0].score > 0 else None
    return RaceResult(prompt=user_prompt, winner=winner,
                      leaderboard=results,
                      started_at=started, finished_at=time.time())
