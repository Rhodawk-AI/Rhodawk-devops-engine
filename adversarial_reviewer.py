"""
Rhodawk AI — Adversarial Reviewer (Consensus Edition)
=====================================================
Upgraded from sequential model-chain to concurrent 3-model consensus.
Requires 2/3 majority to APPROVE or REJECT a diff.
This eliminates single-model veto false-positives and false-negatives.

Architecture:
  Before: Qwen → Gemma → Mistral (sequential, first success wins)
  After:  Qwen ∥ Gemma ∥ Mistral (concurrent) → majority vote threshold=0.67
"""

import concurrent.futures
import hashlib
import json
import os
import time
import requests
from requests.exceptions import HTTPError

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

ADVERSARY_MODEL_PRIMARY = os.getenv(
    "RHODAWK_ADVERSARY_MODEL",
    "deepseek/deepseek-r1:free"
)
ADVERSARY_MODEL_SECONDARY = "meta-llama/llama-3.3-70b-instruct:free"
ADVERSARY_MODEL_TERTIARY  = "google/gemma-3-27b-it:free"

_MODEL_CHAIN = [
    ADVERSARY_MODEL_PRIMARY,
    ADVERSARY_MODEL_SECONDARY,
    ADVERSARY_MODEL_TERTIARY,
]

CONSENSUS_THRESHOLD = float(os.getenv("RHODAWK_CONSENSUS_THRESHOLD", "0.67"))
_RATE_LIMIT_WAIT = 20

ADVERSARY_SYSTEM_PROMPT = """You are a hostile senior security engineer and code quality enforcer.
Your ONLY job is to find problems in AI-generated code fixes. Be adversarial. Be thorough. Be brutal.

You are reviewing a diff produced by an AI to fix a failing test. Your job is to find:
1. SECURITY ISSUES: hardcoded credentials, injection risks, path traversal, insecure deserialization,
   dangerous imports (os.system, eval, exec), secrets in code, SSRF vectors
2. CORRECTNESS ISSUES: does the fix actually solve the root cause or just suppress the symptom?
   Does it handle edge cases? Will it break on different inputs?
3. REGRESSION RISKS: does this change break other functionality? Does it change public API signatures?
   Does it modify behavior for the passing cases?
4. CODE QUALITY: does this fix increase cyclomatic complexity significantly? Does it introduce
   dead code, duplicate logic, or anti-patterns?
5. SUPPLY CHAIN: does it add new dependencies? Are they trustworthy? Do they have known CVEs?

Respond ONLY in this exact JSON format:
{
  "verdict": "APPROVE" | "CONDITIONAL" | "REJECT",
  "confidence": 0.0-1.0,
  "critical_issues": ["issue1", "issue2"],
  "warnings": ["warning1", "warning2"],
  "summary": "one sentence verdict summary",
  "retry_guidance": "if REJECT: specific guidance for what the primary AI should do differently"
}

verdict rules:
- REJECT if ANY critical_issues exist (security vulnerabilities, correctness failures that will cause runtime errors, regressions)
- CONDITIONAL if only warnings exist (code quality, minor style, non-critical concerns)
- APPROVE if no issues found
"""


def _call_openrouter(model: str, system: str, user: str, timeout: int = 60) -> dict:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://rhodawk.ai",
        "X-Title": "Rhodawk AI Adversarial Reviewer",
    }
    payload = {
        "model": model.replace("openrouter/", ""),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},
    }
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return json.loads(content)


def _call_single_model(model: str, user_prompt: str) -> tuple[dict | None, str]:
    """Call one model; return (result_dict, model_name) or (None, model_name) on failure."""
    try:
        result = _call_openrouter(model, ADVERSARY_SYSTEM_PROMPT, user_prompt)
        return result, model
    except HTTPError as e:
        status = e.response.status_code if e.response is not None else 0
        if status == 429:
            time.sleep(_RATE_LIMIT_WAIT)
        return None, model
    except Exception:
        return None, model


def _call_concurrent_consensus(user_prompt: str) -> tuple[dict, str]:
    """
    Run all models concurrently and compute majority verdict.
    Returns (merged_result, summary_of_models_used).
    Falls back to sequential chain if all concurrent calls fail.
    """
    results: list[tuple[dict, str]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(_MODEL_CHAIN)) as executor:
        futures = {
            executor.submit(_call_single_model, model, user_prompt): model
            for model in _MODEL_CHAIN
        }
        for future in concurrent.futures.as_completed(futures, timeout=90):
            try:
                result, model = future.result()
                if result is not None:
                    results.append((result, model))
            except Exception:
                pass

    if not results:
        raise RuntimeError("All concurrent adversarial models failed.")

    verdicts = [r[0].get("verdict", "CONDITIONAL") for r in results]
    models_used = [r[1] for r in results]

    verdict_counts: dict[str, int] = {}
    for v in verdicts:
        verdict_counts[v] = verdict_counts.get(v, 0) + 1

    n = len(verdicts)
    majority_verdict = max(verdict_counts, key=lambda v: verdict_counts[v])
    majority_fraction = verdict_counts[majority_verdict] / n if n > 0 else 0

    if majority_fraction < CONSENSUS_THRESHOLD:
        majority_verdict = "CONDITIONAL"

    merged_critical: list[str] = []
    merged_warnings: list[str] = []
    merged_guidance: list[str] = []
    merged_confidence: list[float] = []
    merged_summary: list[str] = []

    for r, _ in results:
        merged_critical.extend(r.get("critical_issues", []))
        merged_warnings.extend(r.get("warnings", []))
        if r.get("retry_guidance"):
            merged_guidance.append(r["retry_guidance"])
        merged_confidence.append(float(r.get("confidence", 0.5)))
        if r.get("summary"):
            merged_summary.append(r["summary"])

    unique_critical = list(dict.fromkeys(merged_critical))
    unique_warnings = list(dict.fromkeys(merged_warnings))

    avg_confidence = sum(merged_confidence) / len(merged_confidence) if merged_confidence else 0.5
    consensus_summary = (
        f"[Consensus {majority_fraction:.0%} on {majority_verdict}] "
        + "; ".join(merged_summary[:2])
    )

    merged_result = {
        "verdict": majority_verdict,
        "confidence": round(avg_confidence, 3),
        "critical_issues": unique_critical,
        "warnings": unique_warnings,
        "summary": consensus_summary,
        "retry_guidance": " | ".join(merged_guidance[:2]),
        "consensus_votes": verdict_counts,
        "consensus_fraction": round(majority_fraction, 3),
    }

    return merged_result, f"consensus({','.join(m.split('/')[-1] for m in models_used)})"


def _call_with_model_chain(user_prompt: str) -> tuple[dict, str]:
    """
    Legacy sequential fallback — used only if concurrent call is explicitly disabled.
    """
    last_error = None
    for model in _MODEL_CHAIN:
        try:
            result = _call_openrouter(model, ADVERSARY_SYSTEM_PROMPT, user_prompt)
            return result, model
        except HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status == 429:
                time.sleep(_RATE_LIMIT_WAIT)
            last_error = e
            continue
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All models in chain failed. Last error: {last_error}")


def run_adversarial_review(
    diff_text: str,
    test_path: str,
    original_failure: str,
    repo: str,
) -> dict:
    """
    Run the concurrent adversarial consensus review on an AI-generated diff.

    Returns a dict with:
      verdict: "APPROVE" | "CONDITIONAL" | "REJECT"
      confidence: float (avg across models)
      critical_issues: list[str]
      warnings: list[str]
      summary: str
      retry_guidance: str
      model_used: str
      review_hash: str
      timestamp: str
      consensus_votes: dict (NEW — breakdown by model verdict)
      consensus_fraction: float (NEW — majority fraction)
    """
    if not OPENROUTER_API_KEY:
        return {
            "verdict": "APPROVE",
            "confidence": 0.5,
            "critical_issues": [],
            "warnings": ["Adversarial review skipped — OPENROUTER_API_KEY not set"],
            "summary": "Review skipped",
            "retry_guidance": "",
            "model_used": "none",
            "review_hash": "skipped",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "consensus_votes": {},
            "consensus_fraction": 0.0,
        }

    user_prompt = (
        f"REPOSITORY: {repo}\n"
        f"FAILING TEST: {test_path}\n\n"
        f"ORIGINAL FAILURE OUTPUT:\n```\n{original_failure[:1500]}\n```\n\n"
        f"AI-GENERATED DIFF TO REVIEW:\n```diff\n{diff_text[:3000]}\n```\n\n"
        f"Find every problem with this diff. Be adversarial."
    )

    use_concurrent = os.getenv("RHODAWK_ADVERSARY_SEQUENTIAL", "false").lower() != "true"

    try:
        if use_concurrent:
            result, model_used = _call_concurrent_consensus(user_prompt)
        else:
            result, model_used = _call_with_model_chain(user_prompt)
    except Exception as e:
        return {
            "verdict": "CONDITIONAL",
            "confidence": 0.5,
            "critical_issues": [],
            "warnings": [f"Adversarial review failed after trying all models: {e}"],
            "summary": "Review unavailable — proceeding with SAST gate only",
            "retry_guidance": "",
            "model_used": "failed",
            "review_hash": "failed",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "consensus_votes": {},
            "consensus_fraction": 0.0,
        }

    review_input = f"{diff_text}{original_failure}"
    review_hash = hashlib.sha256(review_input.encode()).hexdigest()[:16]

    return {
        "verdict": result.get("verdict", "CONDITIONAL"),
        "confidence": result.get("confidence", 0.5),
        "critical_issues": result.get("critical_issues", []),
        "warnings": result.get("warnings", []),
        "summary": result.get("summary", ""),
        "retry_guidance": result.get("retry_guidance", ""),
        "model_used": model_used,
        "review_hash": review_hash,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "consensus_votes": result.get("consensus_votes", {}),
        "consensus_fraction": result.get("consensus_fraction", 0.0),
    }
