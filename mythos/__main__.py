"""
End-to-end self-test for the Mythos package.

Run with::

    python -m mythos               # full diagnostic + sample campaign
    python -m mythos status        # availability matrix only
    python -m mythos campaign /path/to/repo

Exits with non-zero status if any *required* component fails to import.
Optional native tools (Joern, AFL++, KLEE, Frida, …) are reported as
"unavailable" but never fail the self-test.
"""

from __future__ import annotations

import json
import os
import sys
import traceback


from mythos.diagnostics import (
    availability_matrix, reasoning_check, learning_check, api_check, mcp_check,
)


def _safe(label, fn):
    try:
        return {"label": label, "ok": True, "value": fn()}
    except Exception as exc:  # noqa: BLE001
        return {"label": label, "ok": False, "error": f"{type(exc).__name__}: {exc}"}


def sample_campaign(target_repo: str | None = None) -> dict:
    from mythos.agents.orchestrator import MythosOrchestrator
    target = {
        "repo": target_repo or os.getcwd(),
        "repo_path": target_repo or os.getcwd(),
        "branch": "main",
        "languages": ["python"],
        "frameworks": ["flask"],
        "dependencies": ["pickle"],
        "harness_dir": "/tmp/mythos-research",
    }
    os.makedirs(target["harness_dir"], exist_ok=True)
    orch = MythosOrchestrator(max_iterations=1)
    return orch.run_campaign(target)


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    cmd = (argv[0] if argv else "status").lower()

    print("Mythos self-test starting …")
    out: dict[str, object] = {}

    out["matrix"]    = _safe("availability_matrix", availability_matrix)
    out["reasoning"] = _safe("reasoning",            reasoning_check)
    out["learning"]  = _safe("learning",             learning_check)
    out["api"]       = _safe("api",                  api_check)
    out["mcp"]       = _safe("mcp",                  mcp_check)

    if cmd in ("campaign", "full"):
        target_repo = argv[1] if len(argv) > 1 else None
        out["campaign"] = _safe("campaign", lambda: sample_campaign(target_repo))

    print(json.dumps(out, indent=2, default=str))
    bad = [k for k, v in out.items() if isinstance(v, dict) and not v.get("ok", True)]
    if bad:
        print(f"\n✘ FAIL: {bad}", file=sys.stderr)
        return 1
    print("\n✔ OK — Mythos self-test passed")
    return 0


if __name__ == "__main__":  # pragma: no cover
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
