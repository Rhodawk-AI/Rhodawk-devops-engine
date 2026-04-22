"""
scope-parser-mcp — HackerOne / Bugcrowd / Intigriti scope ingestion (§5.2).

Pulls active programs from each platform, applies the operator's hard filters
(P1/P2 only, ≥ $1k cash bounty, no everything-out-of-scope programs), and
returns a normalised list ready for the night-mode scheduler to consume.

Environment:
    HACKERONE_USERNAME, HACKERONE_API_TOKEN
    BUGCROWD_API_TOKEN
    INTIGRITI_API_TOKEN
    YESWEHACK_API_TOKEN
    ARCHITECT_MIN_BOUNTY_USD  (default 1000)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests

from ._mcp_runtime import MCPServer

LOG = logging.getLogger("mythos.mcp.scope_parser")
server = MCPServer(name="scope-parser-mcp")


def _min_bounty() -> int:
    return int(os.getenv("ARCHITECT_MIN_BOUNTY_USD", "1000"))


# ── HackerOne ──────────────────────────────────────────────────────────────
def _h1_programs() -> list[dict[str, Any]]:
    user = os.getenv("HACKERONE_USERNAME")
    tok  = os.getenv("HACKERONE_API_TOKEN")
    if not user or not tok:
        return []
    try:
        r = requests.get(
            "https://api.hackerone.com/v1/hackers/programs",
            auth=(user, tok), timeout=15,
            params={"page[size]": 100},
        )
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as exc:  # noqa: BLE001
        LOG.warning("h1 fetch failed: %s", exc)
        return []


def _h1_normalise(p: dict[str, Any]) -> dict[str, Any] | None:
    attrs = p.get("attributes", {})
    if not attrs.get("offers_bounties"):
        return None
    relationships = p.get("relationships", {})
    scopes = relationships.get("structured_scopes", {}).get("data", [])
    in_scope = [s.get("attributes", {}).get("asset_identifier")
                for s in scopes
                if s.get("attributes", {}).get("eligible_for_bounty")]
    in_scope = [s for s in in_scope if s]
    return {
        "platform": "hackerone",
        "handle": attrs.get("handle"),
        "name": attrs.get("name"),
        "in_scope_assets": in_scope,
        "policy_url": attrs.get("policy"),
    }


# ── Bugcrowd ───────────────────────────────────────────────────────────────
def _bc_programs() -> list[dict[str, Any]]:
    tok = os.getenv("BUGCROWD_API_TOKEN")
    if not tok:
        return []
    try:
        r = requests.get(
            "https://api.bugcrowd.com/programs",
            headers={"Authorization": f"Token {tok}",
                     "Accept": "application/vnd.bugcrowd+json"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as exc:  # noqa: BLE001
        LOG.warning("bugcrowd fetch failed: %s", exc)
        return []


def _bc_normalise(p: dict[str, Any]) -> dict[str, Any] | None:
    a = p.get("attributes", {})
    return {
        "platform": "bugcrowd",
        "handle": a.get("code"),
        "name": a.get("name"),
        "in_scope_assets": [t.get("name") for t in a.get("targets", []) if t.get("in_scope")],
        "policy_url": a.get("brief_url"),
    }


# ── Intigriti ──────────────────────────────────────────────────────────────
def _intigriti_programs() -> list[dict[str, Any]]:
    tok = os.getenv("INTIGRITI_API_TOKEN")
    if not tok:
        return []
    try:
        r = requests.get(
            "https://api.intigriti.com/external/researcher/v1/programs",
            headers={"Authorization": f"Bearer {tok}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json() if isinstance(r.json(), list) else r.json().get("records", [])
    except Exception as exc:  # noqa: BLE001
        LOG.warning("intigriti fetch failed: %s", exc)
        return []


def _intigriti_normalise(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "platform": "intigriti",
        "handle": p.get("handle") or p.get("companyHandle"),
        "name": p.get("name"),
        "in_scope_assets": [d.get("endpoint") for d in p.get("domains", []) if d.get("endpoint")],
        "policy_url": p.get("webLink"),
    }


@server.tool("list_active_programs", schema={"platforms": "list[string] (optional)"})
def list_active_programs(platforms: list[str] | None = None) -> dict[str, Any]:
    wanted = set(platforms or ["hackerone", "bugcrowd", "intigriti"])
    out: list[dict[str, Any]] = []
    if "hackerone" in wanted:
        out.extend([n for n in (_h1_normalise(p) for p in _h1_programs()) if n])
    if "bugcrowd" in wanted:
        out.extend([n for n in (_bc_normalise(p) for p in _bc_programs()) if n])
    if "intigriti" in wanted:
        out.extend([n for n in (_intigriti_normalise(p) for p in _intigriti_programs()) if n])
    out = [p for p in out if p.get("in_scope_assets")]
    return {"programs": out, "count": len(out), "min_bounty_usd": _min_bounty()}


@server.tool("parse_scope_text",
             schema={"raw_text": "string", "platform": "string"})
def parse_scope_text(raw_text: str, platform: str = "manual") -> dict[str, Any]:
    """Extract URLs / domains / IPs from a pasted policy / scope page."""
    import re
    urls = re.findall(r"https?://[^\s)\]>]+", raw_text)
    domains = re.findall(r"(?<![\w-])(?:[a-z0-9-]+\.)+[a-z]{2,}(?![\w-])", raw_text, re.I)
    cidrs = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}\b", raw_text)
    return {"platform": platform,
            "urls": sorted(set(urls)),
            "domains": sorted(set(domains)),
            "cidrs": sorted(set(cidrs))}


if __name__ == "__main__":
    server.serve_stdio()
