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
"""

import os
import time
from dataclasses import dataclass, field
from typing import Optional

MAX_RETRIES = int(os.getenv("RHODAWK_MAX_RETRIES", "5"))
ADVERSARIAL_REJECTION_MULTIPLIER = int(os.getenv("RHODAWK_ADVERSARIAL_REJECTION_MULTIPLIER", "0"))
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

    sections.append(
        f"\nINSTRUCTIONS:\n"
        f"1. Fix the source code in '{src_file}' or 'requirements.txt' ONLY. Do NOT modify test files.\n"
        f"2. Use the 'fetch-docs' MCP tool to look up library documentation if needed.\n"
        f"3. Work on branch '{branch_name}'. Commit the minimal fix when complete.\n"
        f"4. The fix MUST be different from all previous attempts.\n"
        f"5. Ensure the fix is minimal and does not introduce regressions."
    )

    return "\n".join(sections)


def build_initial_prompt(
    test_path: str,
    src_file: str,
    branch_name: str,
    failure_output: str,
    similar_fixes: list[dict],
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

    sections.append(
        f"\nINSTRUCTIONS:\n"
        f"1. If there is an import error or version conflict, use 'fetch-docs' MCP to look up "
        f"   documentation on docs.python.org or pypi.org.\n"
        f"2. Fix '{src_file}' or 'requirements.txt' to make the test pass. Do NOT modify test files.\n"
        f"3. Work on branch '{branch_name}'. Commit the minimal fix when complete.\n"
        f"4. The fix must be minimal and must not introduce regressions."
    )

    return "\n".join(sections)
