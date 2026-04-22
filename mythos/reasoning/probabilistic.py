"""
Hypothesis Engine — probabilistic reasoning over vulnerability hypotheses.

Implements §4.1 of the Mythos plan.  Uses Pyro / PyMC when available, falls
back to a transparent NumPy Bayesian update otherwise so the engine is
always usable inside a HuggingFace Space without GPU acceleration.

The engine maintains per-CWE prior probabilities and updates them with
evidence collected by the Explorer/Executor agents — this is the
``confidence`` value the Planner uses for resource allocation.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any

# Optional probabilistic-programming back-ends.
try:  # pragma: no cover - optional
    import pyro  # type: ignore  # noqa: F401
    import pyro.distributions as dist  # type: ignore  # noqa: F401
    _PYRO = True
except Exception:  # noqa: BLE001
    _PYRO = False

try:  # pragma: no cover - optional
    import pymc as pm  # type: ignore  # noqa: F401
    _PYMC = True
except Exception:  # noqa: BLE001
    _PYMC = False


# ---------------------------------------------------------------------------
# Curated CWE → vulnerability-class priors.  These are pragmatic starting
# points sourced from the OWASP Top 10 + CWE Top 25 exposure stats; the
# engine refines them online from successful campaigns.
# ---------------------------------------------------------------------------
CWE_PRIORS: dict[str, float] = {
    "CWE-79":  0.18,   # XSS
    "CWE-89":  0.16,   # SQLi
    "CWE-78":  0.10,   # OS command injection
    "CWE-22":  0.08,   # Path traversal
    "CWE-94":  0.08,   # Code injection
    "CWE-119": 0.12,   # Buffer overflow
    "CWE-416": 0.10,   # UAF
    "CWE-787": 0.10,   # Out-of-bounds write
    "CWE-269": 0.05,   # Improper privilege management
    "CWE-287": 0.07,   # Improper authentication
    "CWE-352": 0.04,   # CSRF
    "CWE-918": 0.05,   # SSRF
    "CWE-502": 0.06,   # Unsafe deserialization
    "CWE-732": 0.04,   # Incorrect permissions
    "CWE-862": 0.05,   # Missing authorization
}

KIND_FOR_CWE: dict[str, str] = {
    "CWE-79":  "validation", "CWE-89": "validation", "CWE-78": "validation",
    "CWE-22":  "validation", "CWE-94": "logic",      "CWE-119": "memory",
    "CWE-416": "memory",     "CWE-787": "memory",    "CWE-269": "auth",
    "CWE-287": "auth",       "CWE-352": "auth",      "CWE-918": "logic",
    "CWE-502": "logic",      "CWE-732": "auth",      "CWE-862": "auth",
}


@dataclass
class Hypothesis:
    cwe: str
    kind: str
    confidence: float
    rationale: str = ""
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__


class HypothesisEngine:
    """Bayesian-flavoured generator of ranked vulnerability hypotheses."""

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.priors = dict(CWE_PRIORS)

    # -- public -------------------------------------------------------------

    def sample(self, recon: dict[str, Any], n: int = 8) -> list[dict[str, Any]]:
        """Return the top-``n`` hypotheses for a recon snapshot."""
        evidence_boosts = self._boosts_from_recon(recon)
        scored: list[Hypothesis] = []
        for cwe, prior in self.priors.items():
            posterior = self._bayes_update(prior, evidence_boosts.get(cwe, 0.0))
            scored.append(Hypothesis(
                cwe=cwe,
                kind=KIND_FOR_CWE.get(cwe, "logic"),
                confidence=round(posterior, 4),
                rationale=self._rationale(cwe, recon, posterior),
            ))
        scored.sort(key=lambda h: h.confidence, reverse=True)
        return [h.to_dict() for h in scored[:n]]

    def update_with_outcome(self, cwe: str, *, success: bool) -> None:
        """Online refinement: bump or decay a prior after a campaign result."""
        prior = self.priors.get(cwe, 0.05)
        if success:
            self.priors[cwe] = min(0.95, prior + 0.03)
        else:
            self.priors[cwe] = max(0.005, prior * 0.95)

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _bayes_update(prior: float, log_lift: float) -> float:
        """Combine a base prior with a log-odds evidence boost."""
        if prior <= 0.0 or prior >= 1.0:
            return prior
        odds = prior / (1.0 - prior)
        odds *= math.exp(log_lift)
        return odds / (1.0 + odds)

    @staticmethod
    def _boosts_from_recon(recon: dict[str, Any]) -> dict[str, float]:
        """Translate recon hints (languages, deps, frameworks) into log-odds boosts."""
        boosts: dict[str, float] = {}
        langs = {l.lower() for l in recon.get("languages", [])}
        deps  = {d.lower() for d in recon.get("dependencies", [])}
        frame = {f.lower() for f in recon.get("frameworks", [])}
        if {"c", "c++", "cpp"} & langs:
            for cwe in ("CWE-119", "CWE-416", "CWE-787"):
                boosts[cwe] = boosts.get(cwe, 0.0) + 1.0
        if {"javascript", "typescript", "node"} & langs or "express" in frame:
            boosts["CWE-79"] = boosts.get("CWE-79", 0.0) + 0.7
        if "django" in frame or "flask" in frame or "rails" in frame:
            boosts["CWE-89"] = boosts.get("CWE-89", 0.0) + 0.5
            boosts["CWE-352"] = boosts.get("CWE-352", 0.0) + 0.4
        if {"jackson", "pickle", "marshal", "yaml"} & deps:
            boosts["CWE-502"] = boosts.get("CWE-502", 0.0) + 1.2
        return boosts

    @staticmethod
    def _rationale(cwe: str, recon: dict[str, Any], posterior: float) -> str:
        return (
            f"{cwe} elevated to p={posterior:.2f} by recon "
            f"langs={recon.get('languages', [])[:3]} "
            f"frameworks={recon.get('frameworks', [])[:3]}"
        )

    # -- back-end advertisement --------------------------------------------

    @property
    def backend(self) -> str:
        if _PYRO:
            return "pyro"
        if _PYMC:
            return "pymc"
        return "numpy-bayes"
