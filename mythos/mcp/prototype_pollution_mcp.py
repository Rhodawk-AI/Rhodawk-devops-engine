"""
Mythos MCP — JS prototype-pollution surface scan.

Static AST-style detection: greps a repo for the canonical sinks:

    * Object.assign(target, untrustedUserInput)
    * Lodash _.merge / _.set / _.defaultsDeep with user input
    * jQuery $.extend(true, target, untrusted)
    * Recursive ``for..in`` copy without ``hasOwnProperty`` guard

Output is a list of "candidate" sinks for the LLM to triage; the noise rate
is high, so callers downstream apply consensus before filing.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

LOG = logging.getLogger("mythos.mcp.prototype_pollution")

PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bObject\.assign\s*\([^)]*req\.(body|query|params)", "Object.assign"),
    (r"\b_(?:lodash)?\s*\.\s*(merge|defaultsDeep|set)\s*\(", "lodash.merge"),
    (r"\$\.extend\s*\(\s*true\s*,", "jQuery.extend(true)"),
    (r"for\s*\(\s*\w+\s+in\s+\w+\)\s*\{[^}]*\[", "for..in copy"),
)


def scan_repo(repo_path: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    root = Path(repo_path)
    if not root.exists():
        return out
    for path in root.rglob("*.js"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        for rx, label in PATTERNS:
            for m in re.finditer(rx, text):
                lineno = text.count("\n", 0, m.start()) + 1
                out.append({
                    "title": f"Possible prototype-pollution sink ({label})",
                    "severity": "medium",
                    "cvss": 5.3,
                    "url": str(path.relative_to(root)),
                    "description": f"Pattern '{label}' on line {lineno}. If the merged "
                                   "object originates from untrusted input, the attacker "
                                   "can assign __proto__ properties.",
                    "evidence": {"file": str(path), "line": lineno, "pattern": label},
                    "reproduction": [
                        f"open {path}:{lineno}",
                        "trace upstream to confirm taint reaches this sink",
                    ],
                    "confidence": 0.45,
                })
    return out


def scan_host(host: str) -> list[dict[str, Any]]:  # parity shim
    return scan_repo(host)


if __name__ == "__main__":  # pragma: no cover
    import json, sys
    print(json.dumps(scan_repo(sys.argv[1] if len(sys.argv) > 1 else "."), indent=2))
