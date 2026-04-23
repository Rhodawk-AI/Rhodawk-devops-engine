"""
Mythos MCP — semantic skill selector exposed as an MCP-compatible service.

Wraps :mod:`architect.skill_selector` so any LLM tool-call can ask:

    selector.select(task=..., languages=[...], phase=...) -> str

The MCP runtime lazy-loads this module via ``python -m
mythos.mcp.skill_selector_mcp``; when invoked from the CLI it reads JSON
from stdin and writes JSON to stdout, making it trivially scriptable from
shell / orchestrator code.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

LOG = logging.getLogger("mythos.mcp.skill_selector")


def select(task: str, *, languages: list[str] | None = None,
           tech: list[str] | None = None, phase: str = "static",
           top_k: int = 5, pin: list[str] | None = None) -> dict[str, Any]:
    try:
        from architect import skill_selector
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "context": ""}
    ctx = skill_selector.select_for_task(
        task, repo_languages=languages, repo_tech_stack=tech,
        attack_phase=phase, top_k=top_k, pin=pin,
    )
    explain = skill_selector.explain(
        task, repo_languages=languages, repo_tech_stack=tech,
        attack_phase=phase, top_k=top_k,
    )
    return {"ok": True, "context": ctx, "matches": explain.get("matches", []),
            "engine": explain.get("engine")}


def main() -> int:
    """JSON-in / JSON-out CLI for orchestrator integration."""
    raw = sys.stdin.read() or "{}"
    try:
        req = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        json.dump({"ok": False, "error": f"bad json: {exc}"}, sys.stdout)
        return 2
    out = select(
        task=str(req.get("task", "")),
        languages=req.get("languages") or [],
        tech=req.get("tech") or [],
        phase=str(req.get("phase", "static")),
        top_k=int(req.get("top_k", 5)),
        pin=req.get("pin") or [],
    )
    json.dump(out, sys.stdout, indent=2)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
