"""
Joern Code Property Graph bridge.

Joern ships as a JVM CLI.  This bridge is a thin, robust subprocess wrapper
that:

  1. Detects the ``joern`` binary on ``$PATH`` (or ``$JOERN_HOME/bin``).
  2. Imports a target codebase (``importCode``).
  3. Runs hypothesis-driven CPG queries (taint, call-chains, dataflow).
  4. Returns parsed JSON results.

If Joern is not installed the bridge raises ``MythosToolUnavailable`` so the
orchestrator transparently routes around it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Any

from .. import MythosToolUnavailable

# Hypothesis-class → Joern query template.
_QUERY_TEMPLATES: dict[str, str] = {
    "validation": (
        'cpg.call.name("(eval|exec|system|popen|Runtime.getRuntime.*exec)")'
        '.location.toJsonPretty'
    ),
    "memory": (
        'cpg.call.name("(strcpy|gets|sprintf|memcpy)")'
        '.location.toJsonPretty'
    ),
    "auth": (
        'cpg.method.name(".*[Aa]uth.*").parameter.name(".*").location.toJsonPretty'
    ),
    "logic": (
        'cpg.method.controlStructure.code(".*TODO.*|.*FIXME.*").location.toJsonPretty'
    ),
}


class JoernBridge:
    def __init__(self, joern_home: str | None = None):
        self.joern = (
            shutil.which("joern")
            or (os.path.join(joern_home, "bin", "joern") if joern_home else None)
            or os.path.join(os.environ.get("JOERN_HOME", ""), "bin", "joern")
        )

    def available(self) -> bool:
        return bool(self.joern and os.path.exists(self.joern))

    def query(self, repo_path: str, hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.available():
            return []
        kinds = {h.get("kind", "logic") for h in hypotheses}
        results: list[dict[str, Any]] = []
        for kind in kinds:
            tpl = _QUERY_TEMPLATES.get(kind)
            if not tpl:
                continue
            results.extend(self._run_query(repo_path, tpl, kind))
        return results

    def _run_query(self, repo_path: str, query: str, kind: str) -> list[dict[str, Any]]:
        with tempfile.NamedTemporaryFile("w", suffix=".sc", delete=False) as fh:
            fh.write(f'importCode("{repo_path}")\n{query}\n')
            script = fh.name
        try:
            proc = subprocess.run(
                [self.joern, "--script", script, "--nocolors"],
                capture_output=True, text=True, timeout=600,
            )
            try:
                payload = json.loads(proc.stdout.strip().splitlines()[-1])
            except Exception:
                payload = {"raw": proc.stdout[-2000:]}
            return [{"kind": kind, "joern": payload}]
        except subprocess.TimeoutExpired:
            return [{"kind": kind, "error": "timeout"}]
        finally:
            try:
                os.unlink(script)
            except OSError:
                pass

    def require(self) -> None:
        if not self.available():
            raise MythosToolUnavailable("joern not on PATH; install via https://joern.io")
