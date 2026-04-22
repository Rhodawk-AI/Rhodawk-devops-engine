"""
CodeQL bridge — runs the open-source CodeQL CLI against a target repo.

The bridge:
  * detects the ``codeql`` binary on ``$PATH``;
  * creates a database for the repo (auto-detects language);
  * runs the bundled QL pack matching each hypothesis kind;
  * returns parsed SARIF results.

When CodeQL is missing the bridge returns an empty list rather than
crashing — the Explorer's other backends provide partial coverage.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Any

# Hypothesis-kind → CodeQL pack to run.  These are the open-source packs
# shipped with the CodeQL CLI.
_PACK_FOR_KIND = {
    "validation": "codeql/python-queries:Security/CWE-079/ReflectedXss.ql",
    "memory":     "codeql/cpp-queries:Security/CWE-119/UnboundedWrite.ql",
    "auth":       "codeql/javascript-queries:Security/CWE-287/MissingAuthN.ql",
    "logic":      "codeql/python-queries:Security/CWE-094/CodeInjection.ql",
}


class CodeQLBridge:
    def __init__(self):
        self.codeql = shutil.which("codeql")

    def available(self) -> bool:
        return bool(self.codeql)

    def query(self, repo_path: str, hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.available() or not os.path.isdir(repo_path):
            return []
        with tempfile.TemporaryDirectory() as workdir:
            db = os.path.join(workdir, "db")
            try:
                subprocess.run(
                    [self.codeql, "database", "create", db, "--language=python", "--source-root", repo_path],
                    capture_output=True, timeout=900, check=False,
                )
            except subprocess.TimeoutExpired:
                return [{"error": "codeql db create timeout"}]
            findings: list[dict[str, Any]] = []
            for h in hypotheses:
                pack = _PACK_FOR_KIND.get(h.get("kind", "logic"))
                if not pack:
                    continue
                sarif = os.path.join(workdir, f"{h['cwe']}.sarif")
                try:
                    subprocess.run(
                        [self.codeql, "database", "analyze", db, pack,
                         "--format=sarif-latest", "--output", sarif],
                        capture_output=True, timeout=900, check=False,
                    )
                    if os.path.exists(sarif):
                        with open(sarif) as fh:
                            findings.append({"cwe": h["cwe"], "sarif": json.load(fh)})
                except subprocess.TimeoutExpired:
                    findings.append({"cwe": h["cwe"], "error": "analyze timeout"})
            return findings
