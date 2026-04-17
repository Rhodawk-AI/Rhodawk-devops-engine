import hashlib
import json
import os
import time
import requests
from requests.exceptions import HTTPError

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Three-model rotation chain — each is a different provider/size to avoid
# hitting the same rate limit bucket twice in a row.
# Override the primary with RHODAWK_ADVERSARY_MODEL env var if needed.
ADVERSARY_MODEL_PRIMARY = os.getenv(
    "RHODAWK_ADVERSARY_MODEL",
    "openrouter/qwen/qwen-2.5-7b-instruct:free"
)
ADVERSARY_MODEL_SECONDARY = "openrouter/google/gemma-2-9b-it:free"
ADVERSARY_MODEL_TERTIARY  = "openrouter/mistralai/mistral-7b-instruct:free"

# Ordered list — tried left to right, skipping on 429 or 404
_MODEL_CHAIN = [
    ADVERSARY_MODEL_PRIMARY,
    ADVERSARY_MODEL_SECONDARY,
    ADVERSARY_MODEL_TERTIARY,
]

# Seconds to wait after a 429 before trying the next model in the chain
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


def _call_with_model_chain(user_prompt: str) -> tuple[dict, str]:
    """
    Try each model in the chain in order.
    On 429 (rate limit): wait _RATE_LIMIT_WAIT seconds then try next model.
    On 404 (model not found): immediately try next model.
    Returns (result_dict, model_used_string).
    Raises RuntimeError if all models fail.
    """
    last_error = None
    for model in _MODEL_CHAIN:
        try:
            result = _call_openrouter(model, ADVERSARY_SYSTEM_PROMPT, user_prompt)
            return result, model
        except HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status == 429:
                # Rate limited — wait before trying next model
                time.sleep(_RATE_LIMIT_WAIT)
                last_error = e
                continue
            elif status == 404:
                # Model not found — skip immediately
                last_error = e
                continue
            else:
                # Other HTTP error — skip to next model
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
    Run the adversarial LLM review on an AI-generated diff.

    Returns a dict with:
      verdict: "APPROVE" | "CONDITIONAL" | "REJECT"
      critical_issues: list[str]
      warnings: list[str]
      summary: str
      retry_guidance: str
      model_used: str
      review_hash: str
      timestamp: str
    """
    if not OPENROUTER_API_KEY:
        return {
            "verdict": "APPROVE",
            "critical_issues": [],
            "warnings": ["Adversarial review skipped — OPENROUTER_API_KEY not set"],
            "summary": "Review skipped",
            "retry_guidance": "",
            "model_used": "none",
            "review_hash": "skipped",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    user_prompt = (
        f"REPOSITORY: {repo}\n"
        f"FAILING TEST: {test_path}\n\n"
        f"ORIGINAL FAILURE OUTPUT:\n```\n{original_failure[:1500]}\n```\n\n"
        f"AI-GENERATED DIFF TO REVIEW:\n```diff\n{diff_text[:3000]}\n```\n\n"
        f"Find every problem with this diff. Be adversarial."
    )

    try:
        result, model_used = _call_with_model_chain(user_prompt)
    except Exception as e:
        return {
            "verdict": "CONDITIONAL",
            "critical_issues": [],
            "warnings": [f"Adversarial review failed after trying all models: {e}"],
            "summary": "Review unavailable — proceeding with SAST gate only",
            "retry_guidance": "",
            "model_used": "failed",
            "review_hash": "failed",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
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
    }
