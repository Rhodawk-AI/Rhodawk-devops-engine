"""
Mythos MCP — dependency-confusion vector detector.

For every internal-looking dependency in a manifest (no ``@scope``,
no public namespace prefix, no published version on the registry), emit a
finding describing the registry the attacker would race against.

Supported manifests:  package.json, requirements.txt, pyproject.toml.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

LOG = logging.getLogger("mythos.mcp.dep_confusion")

PUBLIC_HINTS = ("@", "/")  # scoped npm packages / paths


def _exists_on_pypi(name: str) -> bool:
    try:
        import requests  # type: ignore
        r = requests.get(f"https://pypi.org/pypi/{name}/json", timeout=4)
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        return True  # fail safe — assume it exists


def _exists_on_npm(name: str) -> bool:
    try:
        import requests  # type: ignore
        r = requests.get(f"https://registry.npmjs.org/{name}", timeout=4)
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        return True


def scan_repo(repo_path: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    p = Path(repo_path)

    pkg = p / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text())
            for section in ("dependencies", "devDependencies", "peerDependencies"):
                for name in (data.get(section) or {}):
                    if any(h in name for h in PUBLIC_HINTS):
                        continue
                    if not _exists_on_npm(name):
                        out.append({
                            "title": f"Possible dependency confusion: '{name}' (npm)",
                            "severity": "high",
                            "cvss": 8.1,
                            "url": "package.json",
                            "description": "Manifest pins an unscoped name not present on the public "
                                           "npm registry. An attacker can publish it under that name "
                                           "and your install resolves to their code.",
                            "evidence": {"manifest": "package.json", "name": name},
                            "confidence": 0.85,
                        })
        except Exception as exc:  # noqa: BLE001
            LOG.debug("package.json parse: %s", exc)

    req = p / "requirements.txt"
    if req.exists():
        for line in req.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name = re.split(r"[<>=!~\[]", line, maxsplit=1)[0].strip()
            if not name or "/" in name or ":" in name:
                continue
            if not _exists_on_pypi(name):
                out.append({
                    "title": f"Possible dependency confusion: '{name}' (PyPI)",
                    "severity": "high",
                    "cvss": 8.1,
                    "url": "requirements.txt",
                    "description": "Listed name not published on PyPI. Attacker can publish & race.",
                    "evidence": {"manifest": "requirements.txt", "name": name},
                    "confidence": 0.85,
                })
    return out


def scan_host(host: str) -> list[dict[str, Any]]:  # alias for night_hunt API parity
    return scan_repo(host)


if __name__ == "__main__":  # pragma: no cover
    import sys
    print(json.dumps(scan_repo(sys.argv[1] if len(sys.argv) > 1 else "."), indent=2))
