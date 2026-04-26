"""
GODMODE Consensus — multi-model parallel racing (G0DM0D3-inspired).

Fires the same prompt across 3-N model+style combos in parallel, scores
each response on the ACTS 100-point composite metric, and returns the
winner along with the full leaderboard.  Re-uses the existing model router
so every call honours the hard budget cap and falls back to T5-local when
needed.

ACTS 100-point composite (5 dimensions × 20 points each):
    cwe_presence      — CWE ID cited, correct category          (0-20)
    cvss_quality      — CVSS score, vector string, severity tag  (0-20)
    reproducibility   — numbered steps + copy-paste PoC snippet  (0-20)
    poc_feasibility   — exploit complexity, primitives chain      (0-20)
    patch_quality     — actionable fix, version range, reference  (0-20)

Threshold: ACTS ≥ 72 → surfaced. ACTS < 72 → episodic memory only.

The scorer is a deterministic feature-based heuristic so we never need an
extra model call to judge — but a custom scorer can be passed in.

Public API:
    race(prompt, *, profile, combos=None, scorer=None) -> RaceResult
"""

from __future__ import annotations

import concurrent.futures as _cf
import logging
import os
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


# ── ACTS 100-point composite scorer ────────────────────────────────────────
# 5 dimensions × 20 points each = 100 points total.
# Threshold: ≥ 72 → surface to operator | < 72 → episodic memory only.

_RE_CWE         = re.compile(r"\bCWE-\d+\b", re.IGNORECASE)
_RE_CVSS_SCORE  = re.compile(r"CVSS[v23]*[: ]+(\d+\.?\d*)", re.IGNORECASE)
_RE_CVSS_VECTOR = re.compile(r"AV:[NALP]/AC:[LH]/", re.IGNORECASE)
_RE_REPRO_STEP  = re.compile(r"^\s*(?:\d+\.|step\s*\d|repro)", re.IGNORECASE | re.MULTILINE)
_RE_CODE        = re.compile(r"```|^\s{4}\S", re.MULTILINE)
_RE_POC_KW      = re.compile(r"\b(?:proof.of.concept|poc|harness|payload|exploit|trigger)\b", re.IGNORECASE)
_RE_PRIMITIVE   = re.compile(r"\b(?:use.after.free|overflow|rce|ssrf|idor|oob.read|heap.spray|type.confusion)\b", re.IGNORECASE)
_RE_PATCH       = re.compile(r"\b(?:patch|fix|remediat|sanitiz|valid|encod|escap|mitigat)\b", re.IGNORECASE)
_RE_VERSION     = re.compile(r"(?:<=?\s*v?\d+\.\d+|>=?\s*v?\d+\.\d+|prior to\s+\d+|\d+\.\d+\s*-\s*\d+\.\d+)", re.IGNORECASE)


def default_scorer(response: str) -> tuple[float, dict[str, float]]:
    """
    ACTS 100-point composite heuristic.  Pure-text — never calls an LLM.

    Dimensions (each scored 0-100, then scaled to ×0.20 weight):
      cwe_presence    — CWE ID cited, correct category family
      cvss_quality    — numeric score + vector string present
      reproducibility — numbered reproduction steps + code block
      poc_feasibility — exploit type primitive(s) + PoC keywords
      patch_quality   — actionable fix keywords + version range + file reference
    """
    if not response:
        return 0.0, {
            "cwe_presence": 0.0, "cvss_quality": 0.0,
            "reproducibility": 0.0, "poc_feasibility": 0.0,
            "patch_quality": 0.0,
        }
    txt = response.strip()
    n_lines = txt.count("\n") + 1

    # ── Dimension 1: CWE presence (0-20 pts) ──────────────────────────────
    cwe_matches = _RE_CWE.findall(txt)
    cwe_presence = 0.0
    if cwe_matches:
        cwe_presence += 60.0                          # at least one CWE
        cwe_presence += min(40.0, len(cwe_matches) * 10.0)  # bonus for multiple
    cwe_presence = min(100.0, cwe_presence)

    # ── Dimension 2: CVSS quality (0-20 pts) ──────────────────────────────
    cvss_quality = 0.0
    if _RE_CVSS_SCORE.search(txt):  cvss_quality += 50.0
    if _RE_CVSS_VECTOR.search(txt): cvss_quality += 30.0
    for sev in ("Critical", "High", "Medium"):
        if re.search(rf"\b{sev}\b", txt, re.IGNORECASE):
            cvss_quality += 20.0
            break
    cvss_quality = min(100.0, cvss_quality)

    # ── Dimension 3: Reproducibility (0-20 pts) ───────────────────────────
    n_steps = len(_RE_REPRO_STEP.findall(txt))
    has_code = bool(_RE_CODE.search(txt))
    repro = min(60.0, n_steps * 15.0) + (40.0 if has_code else 0.0)
    if n_lines > 10:
        repro = min(100.0, repro + 10.0)
    repro = min(100.0, repro)

    # ── Dimension 4: PoC feasibility (0-20 pts) ───────────────────────────
    n_poc_kw   = len(_RE_POC_KW.findall(txt))
    n_primitives = len(_RE_PRIMITIVE.findall(txt))
    has_file_ref = bool(re.search(r"[/\w.-]+\.(?:py|js|ts|c|cpp|go|rs|java|sol)\b", txt))
    poc = min(50.0, n_poc_kw * 15.0) + min(30.0, n_primitives * 15.0) + (20.0 if has_file_ref else 0.0)
    poc = min(100.0, poc)

    # ── Dimension 5: Patch quality (0-20 pts) ─────────────────────────────
    n_patch_kw = len(_RE_PATCH.findall(txt))
    has_version = bool(_RE_VERSION.search(txt))
    boilerplate = ["it is important to note", "as an ai", "in conclusion",
                   "i cannot", "i am unable", "let me know"]
    noise_penalty = 15.0 * sum(1 for b in boilerplate if b in txt.lower())
    patch = min(60.0, n_patch_kw * 12.0) + (40.0 if has_version else 0.0) - noise_penalty
    patch = max(0.0, min(100.0, patch))

    # ── ACTS composite: equal 20-pt weight per dimension ─────────────────
    acts = (cwe_presence + cvss_quality + repro + poc + patch) * 0.20
    return round(acts, 2), {
        "cwe_presence":    round(cwe_presence, 1),
        "cvss_quality":    round(cvss_quality, 1),
        "reproducibility": round(repro, 1),
        "poc_feasibility": round(poc, 1),
        "patch_quality":   round(patch, 1),
    }


# ACTS gate threshold — findings below this score go to episodic memory only.
ACTS_SURFACE_THRESHOLD: float = float(os.getenv("ACTS_SURFACE_THRESHOLD", "72.0"))


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

    # ── AutoTune EMA: record winner's ACTS score for model routing ────────
    if winner is not None:
        try:
            model_router.autotune_record(
                task=profile.get("asset_type", "generic"),
                model=winner.model,
                acts_score=winner.score,
            )
        except Exception as exc:  # noqa: BLE001
            LOG.debug("AutoTune record failed: %s", exc)

    return RaceResult(prompt=user_prompt, winner=winner,
                      leaderboard=results,
                      started_at=started, finished_at=time.time())
