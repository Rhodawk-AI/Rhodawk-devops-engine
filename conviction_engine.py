"""
Rhodawk AI — Conviction Engine (Auto-Merge Gate)
================================================
Evaluates whether a successfully verified fix meets the conviction threshold
for autonomous merge without human review.

Conviction criteria (all must be met):
  1. adversarial_confidence >= CONVICTION_CONFIDENCE_MIN (default 0.92)
  2. adversarial_verdict == "APPROVE" (no conditional)
  3. consensus_fraction >= CONVICTION_CONSENSUS_MIN (default 0.85 — 3/3 models agree)
  4. Memory engine found a semantically identical past fix that was human-merged
     (similarity >= CONVICTION_MEMORY_MIN, default 0.85)
  5. test_attempts == 1 (fixed on first try — indicates clean, well-understood fix)
  6. SAST findings == 0 (zero informational findings on the diff)
  7. No new packages introduced in the diff
  8. Deterministic exploit validator returned ValidationVerdict.CONFIRMED
     (INV-020). When ``validation_result`` is provided and the verdict is
     anything other than CONFIRMED, conviction is denied. When it is
     ``None`` the criterion is *advisory* — applicable only to MEDIUM/LOW
     findings where no validator challenge could be synthesised. Callers
     gating CRITICAL/HIGH findings MUST pass a non-``None`` result.

When all criteria pass, auto_merge() is called which uses the GitHub API to
merge the PR directly (no human required).

Enable with: RHODAWK_AUTO_MERGE=true
"""

import os
import time
from typing import Optional

import requests

from exploit_validator import ValidationResult, ValidationVerdict

CONVICTION_CONFIDENCE_MIN = float(os.getenv("RHODAWK_CONVICTION_CONFIDENCE", "0.92"))
CONVICTION_CONSENSUS_MIN  = float(os.getenv("RHODAWK_CONVICTION_CONSENSUS", "0.85"))
CONVICTION_MEMORY_MIN     = float(os.getenv("RHODAWK_CONVICTION_MEMORY_SIM", "0.85"))
AUTO_MERGE_ENABLED        = os.getenv("RHODAWK_AUTO_MERGE", "false").lower() == "true"


def evaluate_conviction(
    adversarial_review: dict,
    similar_fixes: list[dict],
    test_attempts: int,
    sast_findings_count: int,
    new_packages: list[str],
    validation_result: Optional[ValidationResult] = None,
) -> tuple[bool, str]:
    """
    Returns (should_auto_merge, reason_string).
    All criteria must pass for auto-merge to be approved.

    Criterion 8 (INV-020 — deterministic exploit validation):
        ``validation_result`` is the verdict from ``exploit_validator.py``.
        When provided, only ``ValidationVerdict.CONFIRMED`` permits
        auto-merge — every other verdict (REFUTED / PARTIAL / SANDBOX_ERROR)
        denies it. Callers gating CRITICAL/HIGH severity findings MUST
        pass a non-``None`` result; passing ``None`` skips the check
        and is intended only for MEDIUM/LOW findings where no validator
        challenge could be synthesised.
    """
    if not AUTO_MERGE_ENABLED:
        return False, "auto-merge disabled (RHODAWK_AUTO_MERGE != true)"

    verdict = adversarial_review.get("verdict", "CONDITIONAL")
    confidence = float(adversarial_review.get("confidence", 0.0))
    consensus_fraction = float(adversarial_review.get("consensus_fraction", 0.0))

    checks: list[tuple[bool, str]] = [
        (verdict == "APPROVE",
         f"adversarial_verdict must be APPROVE, got {verdict}"),
        (confidence >= CONVICTION_CONFIDENCE_MIN,
         f"adversarial_confidence {confidence:.3f} < {CONVICTION_CONFIDENCE_MIN}"),
        (consensus_fraction >= CONVICTION_CONSENSUS_MIN,
         f"consensus_fraction {consensus_fraction:.3f} < {CONVICTION_CONSENSUS_MIN}"),
        (test_attempts == 1,
         f"fixed in {test_attempts} attempt(s), require 1"),
        (sast_findings_count == 0,
         f"SAST has {sast_findings_count} finding(s), require 0"),
        (not new_packages,
         f"diff introduces new packages: {new_packages}"),
    ]

    memory_check_passed = False
    best_memory_sim = 0.0
    for fix in similar_fixes:
        sim = float(fix.get("similarity", 0.0))
        if sim >= CONVICTION_MEMORY_MIN:
            memory_check_passed = True
            best_memory_sim = sim
            break

    checks.append((
        memory_check_passed,
        f"no human-merged memory match with similarity >= {CONVICTION_MEMORY_MIN} "
        f"(best found: {best_memory_sim:.3f})"
    ))

    # Criterion 8 — INV-020 deterministic exploit validation gate.
    if validation_result is not None:
        confirmed = validation_result.verdict == ValidationVerdict.CONFIRMED
        evidence_excerpt = (validation_result.evidence or "")[:200]
        checks.append((
            confirmed,
            f"INV-020 exploit validation verdict {validation_result.verdict.value} "
            f"(challenge {validation_result.challenge_id}): {evidence_excerpt}",
        ))

    failed = [(passed, reason) for passed, reason in checks if not passed]
    if failed:
        reasons = "; ".join(r for _, r in failed)
        return False, f"conviction not met: {reasons}"

    validation_note = (
        f", validation={validation_result.verdict.value}"
        if validation_result is not None
        else ""
    )
    return True, (
        f"all {len(checks)} conviction criteria passed "
        f"(confidence={confidence:.3f}, consensus={consensus_fraction:.3f}, "
        f"memory_sim={best_memory_sim:.3f}{validation_note})"
    )


def auto_merge_pr(
    repo: str,
    pr_url: str,
    token: str,
    merge_method: str = "squash",
) -> tuple[bool, str]:
    """
    Merge a PR via GitHub API.
    merge_method: "merge" | "squash" | "rebase"
    Returns (success, message).
    """
    if not pr_url or "github.com" not in pr_url:
        return False, f"invalid PR URL: {pr_url}"

    try:
        parts = pr_url.rstrip("/").split("/")
        pr_number = int(parts[-1])
        owner = parts[-4]
        repo_name = parts[-3]
    except (IndexError, ValueError) as e:
        return False, f"could not parse PR URL {pr_url}: {e}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-API-Version": "2022-11-28",
    }

    resp = requests.put(
        f"https://api.github.com/repos/{owner}/{repo_name}/pulls/{pr_number}/merge",
        headers=headers,
        json={
            "merge_method": merge_method,
            "commit_title": f"[Rhodawk] Autonomous merge — conviction threshold met",
            "commit_message": (
                "This PR was autonomously merged by Rhodawk AI after meeting all "
                "conviction criteria:\n"
                "- Adversarial consensus review: APPROVED (3/3 models)\n"
                "- Test verification: GREEN (1 attempt)\n"
                "- SAST gate: CLEAN\n"
                "- Memory match: CONFIRMED (prior human-merged fix)\n"
            ),
        },
        timeout=30,
    )

    if resp.status_code in (200, 201):
        return True, f"auto-merged PR #{pr_number} via {merge_method}"

    return False, f"GitHub merge API returned {resp.status_code}: {resp.text[:200]}"
