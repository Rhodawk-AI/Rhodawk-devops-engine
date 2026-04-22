"""
Semgrep bridge — wraps the existing Semgrep dependency declared in
``requirements.txt`` and exposes a hypothesis-driven scan API.

Falls back to ``semgrep --config=auto`` when no kind-specific config is
matched, and gracefully returns ``[]`` when the binary is unavailable.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

_KIND_CONFIG = {
    "validation": "p/owasp-top-ten",
    "memory":     "p/cwe-top-25",
    "auth":       "p/security-audit",
    "logic":      "p/default",
}


class SemgrepBridge:
    def __init__(self):
        self.bin = shutil.which("semgrep")

    def available(self) -> bool:
        return bool(self.bin)

    def scan(self, repo_path: str, hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.available():
            return []
        configs = {_KIND_CONFIG.get(h.get("kind", "logic"), "p/default") for h in hypotheses}
        results: list[dict[str, Any]] = []
        for cfg in configs:
            try:
                proc = subprocess.run(
                    [self.bin, "--config", cfg, "--json", "--quiet",
                     "--metrics=off", repo_path],
                    capture_output=True, text=True, timeout=900, check=False,
                )
                payload = json.loads(proc.stdout or "{}")
                for r in payload.get("results", []):
                    results.append({
                        "config": cfg,
                        "rule_id": r.get("check_id"),
                        "path": r.get("path"),
                        "line": r.get("start", {}).get("line"),
                        "severity": r.get("extra", {}).get("severity"),
                        "message": r.get("extra", {}).get("message", "")[:400],
                    })
            except (subprocess.TimeoutExpired, json.JSONDecodeError):
                continue
        return results
