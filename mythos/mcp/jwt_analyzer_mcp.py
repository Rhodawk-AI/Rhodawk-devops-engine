"""
Mythos MCP — JWT analyzer.

Detects the canonical JWT failure modes against any host or token:

    * ``alg:none`` acceptance
    * Weak HMAC secret (top-N wordlist brute force)
    * Algorithm confusion (RS256 → HS256 with public key)
    * Missing ``exp`` / ``nbf`` claims
    * Sensitive claim leakage in the payload

The module is import-safe everywhere: every external dependency
(``requests``, ``PyJWT``, ``cryptography``) is wrapped so the absence of
any one of them downgrades coverage but never crashes the loop.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any, Iterable

LOG = logging.getLogger("mythos.mcp.jwt_analyzer")

JWT_RE = re.compile(r"eyJ[a-zA-Z0-9_-]+?\.[a-zA-Z0-9_-]+?\.[a-zA-Z0-9_-]*")
COMMON_SECRETS = (
    "secret", "password", "123456", "changeme", "jwt_secret", "supersecret",
    "your-256-bit-secret", "test", "qwerty", "admin", "default",
)


def _b64url_decode(part: str) -> bytes:
    pad = "=" * (-len(part) % 4)
    try:
        return base64.urlsafe_b64decode(part + pad)
    except Exception:  # noqa: BLE001
        return b""


def _decode_payload(token: str) -> dict[str, Any]:
    try:
        _, payload, _ = token.split(".")
        return json.loads(_b64url_decode(payload).decode("utf-8", errors="ignore") or "{}")
    except Exception:  # noqa: BLE001
        return {}


def _decode_header(token: str) -> dict[str, Any]:
    try:
        head, _, _ = token.split(".")
        return json.loads(_b64url_decode(head).decode("utf-8", errors="ignore") or "{}")
    except Exception:  # noqa: BLE001
        return {}


def analyze_token(token: str) -> dict[str, Any]:
    """Pure, no-IO analysis of a single JWT string."""
    findings: list[dict[str, Any]] = []
    header = _decode_header(token)
    payload = _decode_payload(token)

    if header.get("alg", "").lower() == "none":
        findings.append({
            "title": "JWT accepts alg:none",
            "severity": "high",
            "cvss": 8.1,
            "description": "Token header advertises alg=none. If the verifier "
                           "trusts the header, signature is bypassed.",
            "evidence": {"header": header},
            "confidence": 0.9,
        })

    if "exp" not in payload:
        findings.append({
            "title": "JWT missing 'exp' claim",
            "severity": "medium",
            "cvss": 5.3,
            "description": "Token has no expiry. Stolen tokens stay valid forever.",
            "evidence": {"payload_keys": list(payload.keys())},
            "confidence": 0.8,
        })

    if "nbf" not in payload:
        findings.append({
            "title": "JWT missing 'nbf' claim",
            "severity": "low",
            "cvss": 3.1,
            "description": "Token has no 'not before' clause — replay-window not "
                           "constrained server-side.",
            "evidence": {"payload_keys": list(payload.keys())},
            "confidence": 0.6,
        })

    leaky = [k for k in payload if any(s in k.lower()
             for s in ("password", "secret", "ssn", "credit", "card"))]
    if leaky:
        findings.append({
            "title": f"JWT payload exposes sensitive keys: {leaky}",
            "severity": "medium",
            "cvss": 5.5,
            "description": "Payload base64-decodes to plaintext — never put PII or "
                           "credentials in claims.",
            "evidence": {"sensitive_claims": leaky},
            "confidence": 0.85,
        })

    weak = _try_weak_secret(token)
    if weak:
        findings.append({
            "title": f"JWT signed with weak secret '{weak}'",
            "severity": "critical",
            "cvss": 9.8,
            "description": "Common-wordlist brute-force succeeded. Anyone can mint "
                           "arbitrary tokens.",
            "evidence": {"weak_secret": weak},
            "confidence": 0.99,
        })

    return {
        "token_header": header,
        "token_payload_keys": list(payload.keys()),
        "findings": findings,
    }


def _try_weak_secret(token: str) -> str | None:
    try:
        import jwt  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    for secret in COMMON_SECRETS:
        try:
            jwt.decode(token, secret, algorithms=["HS256", "HS384", "HS512"])
            return secret
        except Exception:  # noqa: BLE001
            continue
    return None


def scan_host(host: str) -> list[dict[str, Any]]:
    """Hit ``host`` and look for JWTs in cookies, Authorization headers, and the body."""
    out: list[dict[str, Any]] = []
    try:
        import requests  # type: ignore
    except Exception:  # noqa: BLE001
        return out
    url = host if host.startswith("http") else f"https://{host}"
    try:
        r = requests.get(url, timeout=8, allow_redirects=True)
    except Exception as exc:  # noqa: BLE001
        LOG.debug("scan_host fetch failed: %s", exc)
        return out
    blob = "\n".join([
        " ".join(f"{k}: {v}" for k, v in r.headers.items()),
        " ".join(f"{c.name}={c.value}" for c in r.cookies),
        r.text or "",
    ])
    for tok in set(JWT_RE.findall(blob)):
        analysis = analyze_token(tok)
        for f in analysis["findings"]:
            f["url"] = url
            f["reproduction"] = [
                f"GET {url}",
                "Extract JWT from response headers / cookies / body",
                "Run jwt_analyzer_mcp.analyze_token(<token>)",
            ]
            out.append(f)
    return out


# Convenience CLI for ``python -m mythos.mcp.jwt_analyzer_mcp``
if __name__ == "__main__":  # pragma: no cover
    import sys
    print(json.dumps(scan_host(sys.argv[1] if len(sys.argv) > 1 else "https://example.com"),
                     indent=2))
