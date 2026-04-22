"""
oss_target_scorer.py — prioritise open-source repositories for the
OSS-Guardian pipeline (Masterplan §2.2).

The scorer takes the GitHub repo metadata that ``repo_harvester.py`` already
fetches and produces a single deterministic float in ``[0.0, 1.0+]``.
Higher scores rank ahead in the OSS-Guardian queue.

Inputs are a plain dict so the scorer stays unit-testable without a network.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any

# Per-language risk weight — memory-unsafe languages and parser-heavy
# runtimes get the highest base weight.
LANG_RISK: dict[str, float] = {
    "c":          1.00,
    "c++":        1.00,
    "cpp":        1.00,
    "asm":        1.00,
    "rust":       0.85,
    "go":         0.70,
    "java":       0.65,
    "kotlin":     0.60,
    "swift":      0.60,
    "objective-c": 0.85,
    "python":     0.55,
    "ruby":       0.55,
    "php":        0.65,
    "javascript": 0.55,
    "typescript": 0.55,
    "solidity":   0.95,
    "scala":      0.55,
}


@dataclass
class TargetScore:
    repo: str
    score: float
    components: dict[str, float]
    rationale: str


def _safe_log10(x: float) -> float:
    return math.log10(max(1.0, float(x) + 1.0))


def _days_since(iso_str: str | None) -> float:
    if not iso_str:
        return 365.0
    try:
        # GitHub returns ISO8601 with a Z suffix.
        t = time.strptime(iso_str.rstrip("Z"), "%Y-%m-%dT%H:%M:%S")
        return max(0.0, (time.time() - time.mktime(t)) / 86400.0)
    except Exception:
        return 365.0


def score_repo(
    repo: dict[str, Any],
    *,
    cve_history_count: int = 0,
    last_security_advisory_iso: str | None = None,
) -> TargetScore:
    """
    Score one repository for vulnerability-research priority.

    ``repo`` should contain at least ``full_name``, ``stargazers_count``,
    ``language`` and (optional) ``network_count`` (dependents).  Extra fields
    are ignored so the scorer is forward-compatible with new GitHub fields.
    """
    name = str(repo.get("full_name") or repo.get("name") or "?")
    stars = int(repo.get("stargazers_count", 0))
    dependents = int(repo.get("network_count") or repo.get("dependents_count") or 0)
    language = str(repo.get("language") or "").lower()
    days_since_patch = _days_since(last_security_advisory_iso)

    c = {
        "stars":       _safe_log10(stars) * 0.20,
        "dependents":  _safe_log10(dependents) * 0.30,
        "freshness":   min(1.0, days_since_patch / 365.0) * 0.20,
        "language":    LANG_RISK.get(language, 0.50) * 0.20,
        "cve_history": _safe_log10(cve_history_count) * 0.10,
    }
    score = round(sum(c.values()), 4)

    rationale_bits: list[str] = []
    if stars >= 10_000:
        rationale_bits.append(f"high-star ({stars:,}★)")
    if dependents >= 1_000:
        rationale_bits.append(f"{dependents:,} dependents")
    if c["language"] >= 0.18:
        rationale_bits.append(f"memory-unsafe language ({language})")
    if cve_history_count > 0:
        rationale_bits.append(f"{cve_history_count} prior CVE(s)")
    rationale = "; ".join(rationale_bits) or "baseline-priority repo"

    return TargetScore(repo=name, score=score, components=c, rationale=rationale)


def rank(repos: list[dict[str, Any]], *, top_k: int = 25) -> list[TargetScore]:
    """Return the top-K repos ordered by descending score."""
    out = [score_repo(r) for r in repos]
    out.sort(key=lambda s: s.score, reverse=True)
    return out[:top_k]
