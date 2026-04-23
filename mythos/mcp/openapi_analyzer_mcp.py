"""
Mythos MCP — OpenAPI / Swagger surface enumerator.

Given a host, find the spec, parse it, and emit:
    * Each route + method as an attack-surface candidate
    * Routes flagged as authenticated / unauthenticated
    * Routes that accept arbitrary file uploads
    * Routes with parameters that look like SQL / NoSQL / SSRF sinks
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

LOG = logging.getLogger("mythos.mcp.openapi_analyzer")

WELL_KNOWN_PATHS = (
    "/openapi.json", "/openapi.yaml", "/openapi.yml",
    "/swagger.json", "/swagger.yaml", "/swagger.yml",
    "/v1/openapi.json", "/v2/openapi.json", "/v3/openapi.json",
    "/api/openapi.json", "/api-docs", "/api/swagger.json",
)

SUSPICIOUS_PARAMS = (
    ("url",       "ssrf"),
    ("redirect",  "open-redirect"),
    ("callback",  "open-redirect"),
    ("file",      "lfi"),
    ("path",      "lfi"),
    ("template",  "ssti"),
    ("query",     "sqli/nosqli"),
    ("filter",    "sqli/nosqli"),
    ("cmd",       "command-injection"),
)


def _fetch_spec(base: str) -> tuple[str, dict[str, Any]] | None:
    try:
        import requests  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    base = base.rstrip("/")
    if not base.startswith("http"):
        base = f"https://{base}"
    for path in WELL_KNOWN_PATHS:
        url = base + path
        try:
            r = requests.get(url, timeout=6)
            if r.status_code == 200 and r.text.strip():
                try:
                    return url, json.loads(r.text)
                except Exception:  # noqa: BLE001
                    try:
                        import yaml  # type: ignore
                        return url, yaml.safe_load(r.text) or {}
                    except Exception:  # noqa: BLE001
                        continue
        except Exception:  # noqa: BLE001
            continue
    return None


def analyze_spec(spec: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    paths = spec.get("paths") or {}
    if not isinstance(paths, dict):
        return out
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method.lower() not in ("get", "post", "put", "delete", "patch", "options"):
                continue
            params = []
            for p in (op.get("parameters") or []):
                if isinstance(p, dict):
                    params.append(str(p.get("name", "")))
            body = op.get("requestBody") or {}
            multipart = "multipart/form-data" in json.dumps(body)
            sec = bool(op.get("security"))
            for name, kind in SUSPICIOUS_PARAMS:
                if any(re.search(rf"\b{name}\b", x, re.I) for x in params):
                    out.append({
                        "title": f"Suspicious parameter '{name}' on {method.upper()} {path}",
                        "severity": "info",
                        "cvss": 0.0,
                        "url": path,
                        "description": f"Likely sink for {kind}. Worth fuzzing manually.",
                        "evidence": {"params": params, "kind": kind},
                        "confidence": 0.4,
                    })
            if multipart and not sec:
                out.append({
                    "title": f"Unauthenticated file upload at {method.upper()} {path}",
                    "severity": "medium",
                    "cvss": 6.1,
                    "url": path,
                    "description": "Endpoint accepts multipart uploads without security scheme.",
                    "evidence": {},
                    "confidence": 0.55,
                })
    return out


def scan_host(host: str) -> list[dict[str, Any]]:
    spec = _fetch_spec(host)
    if not spec:
        return []
    url, doc = spec
    findings = analyze_spec(doc if isinstance(doc, dict) else {})
    for f in findings:
        f["spec_url"] = url
        f["url"] = url
    return findings


if __name__ == "__main__":  # pragma: no cover
    import sys
    print(json.dumps(scan_host(sys.argv[1] if len(sys.argv) > 1 else "https://example.com"),
                     indent=2))
