"""
Rhodawk AI — Closed Verification Loop Engine
=============================================
This is the core capability that separates Rhodawk from every other AI CI tool.

Standard tools: AI generates fix → open PR (no idea if fix works)
Rhodawk:        AI generates fix → re-run tests → if still failing, retry with
                new failure context + what was tried → up to MAX_RETRIES rounds

The loop:
  1. Run tests → get failure output
  2. Dispatch Aider with failure context + memory-retrieved similar fixes
  3. Re-run tests on the modified code
  4. If GREEN → gate through adversarial review → open PR
  5. If STILL RED → append new failure + what was tried → goto 2
  6. After MAX_RETRIES → mark as FAILED, escalate

BUG-002 FIX: Removed hardcoded os.getenv("RHODAWK_REPO_DIR") — repo_dir is now
             passed as a parameter to build_initial_prompt() and build_retry_prompt().
BUG-003 FIX: ADVERSARIAL_REJECTION_MULTIPLIER defaults to 2 (not 0) so adversarial
             rejections get extra retry budget beyond MAX_RETRIES.
"""

import os
import time
from dataclasses import dataclass, field
from typing import Optional
from language_runtime import (
    RuntimeFactory,
    detect_pytest_collection_error,
    route_collection_error_to_hermes,
)

MAX_RETRIES = int(os.getenv("RHODAWK_MAX_RETRIES", "5"))
ADVERSARIAL_REJECTION_MULTIPLIER = int(os.getenv("RHODAWK_ADVERSARIAL_REJECTION_MULTIPLIER", "2"))
RETRY_BACKOFF_SECONDS = 5


@dataclass
class VerificationAttempt:
    attempt_number: int
    prompt_hash: str
    aider_exit_code: int
    test_exit_code: int
    test_output: str
    diff_produced: str
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


@dataclass
class VerificationResult:
    success: bool
    attempts: list[VerificationAttempt] = field(default_factory=list)
    final_diff: str = ""
    final_test_output: str = ""
    failure_reason: str = ""
    total_attempts: int = 0


def build_retry_prompt(
    test_path: str,
    src_file: str,
    branch_name: str,
    original_failure: str,
    attempt_history: list[VerificationAttempt],
    similar_fixes: list[dict],
    repo_dir: str = "/data/repo",
) -> str:
    """
    Build an increasingly rich prompt for each retry attempt.
    Each retry includes:
      - The original failure
      - What was tried in previous attempts and why it failed
      - Retrieved similar successful fixes from memory
    """
    sections = []

    sections.append(
        f"The pytest test '{test_path}' is STILL FAILING. This is attempt "
        f"{len(attempt_history) + 1} of {MAX_RETRIES}.\n"
    )

    sections.append(
        f"ORIGINAL FAILURE:\n```\n{original_failure[:2000]}\n```\n"
    )

    if attempt_history:
        sections.append("PREVIOUS ATTEMPTS THAT DID NOT WORK:")
        for a in attempt_history:
            sections.append(
                f"\nAttempt {a.attempt_number}:\n"
                f"  Test output after fix:\n```\n{a.test_output[:800]}\n```\n"
                f"  Diff that was applied:\n```diff\n{a.diff_produced[:600]}\n```"
            )
        sections.append(
            "\nDo NOT repeat the same fix approach. Analyze why previous attempts failed "
            "and try a fundamentally different strategy.\n"
        )

    if similar_fixes:
        sections.append("\nSIMILAR FIXES FROM MEMORY (from previously healed tests — use as guidance):")
        for i, fix in enumerate(similar_fixes[:2], 1):
            sections.append(
                f"\nSimilar fix {i} (success rate: {fix.get('success_rate', 'unknown')}):\n"
                f"  Failure pattern: {fix.get('failure_signature', '')[:200]}\n"
                f"  Fix applied:\n```diff\n{fix.get('fix_diff', '')[:400]}\n```"
            )

    runtime = RuntimeFactory.for_repo(repo_dir)
    sections.append("INSTRUCTIONS:\n" + runtime.get_fix_prompt_instructions(
        test_path=test_path,
        branch_name=branch_name,
        src_hint=src_file,
    ))

    return "\n".join(sections)


def build_initial_prompt(
    test_path: str,
    src_file: str,
    branch_name: str,
    failure_output: str,
    similar_fixes: list[dict],
    repo_dir: str = "/data/repo",
) -> str:
    sections = []
    sections.append(
        f"The pytest test '{test_path}' is failing:\n\n"
        f"```\n{failure_output[:3000]}\n```\n"
    )

    if similar_fixes:
        sections.append("RELEVANT FIXES FROM MEMORY (similar past failures that were healed):")
        for i, fix in enumerate(similar_fixes[:2], 1):
            sections.append(
                f"\nSimilar case {i} (success rate: {fix.get('success_rate', 'unknown')}):\n"
                f"  Failure: {fix.get('failure_signature', '')[:150]}\n"
                f"  What worked:\n```diff\n{fix.get('fix_diff', '')[:400]}\n```"
            )

    runtime = RuntimeFactory.for_repo(repo_dir)
    sections.append("INSTRUCTIONS:\n" + runtime.get_fix_prompt_instructions(
        test_path=test_path,
        branch_name=branch_name,
        src_hint=src_file,
    ))

    return "\n".join(sections)


# ──────────────────────────────────────────────────────────────────────
# PRE-FLIGHT META-HEALING (Playbook §1)
# ──────────────────────────────────────────────────────────────────────
#
# Before the main retry loop begins, run pytest once to capture the raw
# stderr collection error (if any) and route it to Hermes with priority.
# This stops the loop from burning iterations when the *environment* is
# the problem (missing dependency, broken `tests/__init__.py`, etc.).

def pre_flight_meta_heal(
    test_path: str,
    repo_dir: str = "/data/repo",
    *,
    timeout: int = 60,
) -> dict:
    """Run a single pytest collection to surface pre-flight failures.

    Returns a status dict:
        {"ok": True}                                 — collection clean
        {"ok": False, "kind": ..., "result": ...}    — handed to Hermes
        {"ok": False, "reason": "no_runtime"}        — runtime not available
    """
    try:
        runtime = RuntimeFactory.for_repo(repo_dir)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": "runtime_init_failed", "error": repr(exc)}

    if not hasattr(runtime, "setup_env") or not hasattr(runtime, "run_tests"):
        return {"ok": False, "reason": "no_runtime"}

    try:
        env_config = runtime.setup_env(repo_dir)
    except Exception as exc:  # noqa: BLE001
        # setup_env itself failed — that's a meta-healing candidate too.
        return route_collection_error_to_hermes(
            err=type("E", (), {
                "kind": "env_setup_failure",
                "raw_stderr": repr(exc)[:4000],
                "affected_paths": [],
                "missing_modules": [],
                "returncode": -1,
            })(),
            test_path=test_path,
            repo_dir=repo_dir,
        )

    try:
        output, code = runtime.run_tests(test_path, repo_dir, env_config, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": "run_tests_raised", "error": repr(exc)}

    err = detect_pytest_collection_error(output, returncode=code)
    if err is None:
        return {"ok": True}

    # Found a collection-level failure → hand to Hermes with priority.
    return route_collection_error_to_hermes(
        err=err,
        test_path=test_path,
        repo_dir=repo_dir,
    )
