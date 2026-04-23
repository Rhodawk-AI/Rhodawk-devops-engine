"""
Mythos MCP — CORS misconfiguration analyzer.

Probes a host for the canonical CORS failure modes:

    * Origin reflection (``Access-Control-Allow-Origin: <attacker>``)
    * ``null`` origin acceptance
    * Wildcard with credentials (``ACAO: *`` + ``ACAC: true``)
    * Subdomain wildcard misconfig (``*.target.com`` accepting attacker)
    * Trailing-dot / suffix bypass (``target.com.attacker.com``)
"""

from __future__ import annotations

import logging
from typing import Any

LOG = logging.getLogger("mythos.mcp.cors_analyzer")

PROBE_ORIGINS = [
    "https://evil.example.com",
    "null",
    "https://target.com.evil.example.com",
    "https://eviltarget.com",
]


def _request(host: str, origin: str) -> dict[str, str]:
    try:
        import requests  # type: ignore
    except Exception:  # noqa: BLE001
        return {}
    url = host if host.startswith("http") else f"https://{host}"
    try:
        r = requests.get(url, headers={"Origin": origin}, timeout=8)
        return {k.lower(): v for k, v in r.headers.items()}
    except Exception as exc:  # noqa: BLE001
        LOG.debug("cors probe failed for %s/%s: %s", host, origin, exc)
        return {}


def scan_host(host: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    url = host if host.startswith("http") else f"https://{host}"
    for origin in PROBE_ORIGINS:
        headers = _request(host, origin)
        if not headers:
            continue
        acao = headers.get("access-control-allow-origin", "")
        acac = headers.get("access-control-allow-credentials", "").lower() == "true"
        if not acao:
            continue
        # Reflection
        if acao == origin and origin != "*":
            findings.append({
                "title": "CORS origin reflection",
                "severity": "high" if acac else "medium",
                "cvss": 8.1 if acac else 5.4,
                "url": url,
                "description": f"Server reflects Origin '{origin}' in "
                               f"Access-Control-Allow-Origin. "
                               f"{'With credentials → cross-site data theft.' if acac else ''}",
                "reproduction": [
                    f"curl -i -H 'Origin: {origin}' '{url}'",
                    "Observe Access-Control-Allow-Origin echoes the attacker origin",
                ],
                "evidence": {"origin": origin, "headers": headers},
                "confidence": 0.95 if acac else 0.8,
            })
        # null origin
        if origin == "null" and "null" in acao.lower() and acac:
            findings.append({
                "title": "CORS allows null origin with credentials",
                "severity": "high",
                "cvss": 8.0,
                "url": url,
                "description": "Sandboxed iframes / data: documents can read "
                               "authenticated content.",
                "reproduction": [
                    f"curl -i -H 'Origin: null' '{url}'",
                    "ACAO: null + ACAC: true",
                ],
                "evidence": {"headers": headers},
                "confidence": 0.95,
            })
        # wildcard with credentials
        if acao == "*" and acac:
            findings.append({
                "title": "CORS wildcard origin with credentials",
                "severity": "high",
                "cvss": 8.5,
                "url": url,
                "description": "ACAO:* combined with ACAC:true is forbidden by spec; "
                               "browsers usually block, but old clients / non-browser "
                               "consumers may not.",
                "evidence": {"headers": headers},
                "confidence": 0.85,
            })
    return findings


if __name__ == "__main__":  # pragma: no cover
    import json, sys
    print(json.dumps(scan_host(sys.argv[1] if len(sys.argv) > 1 else "https://example.com"),
                     indent=2))
