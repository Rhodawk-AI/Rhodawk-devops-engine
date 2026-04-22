"""
subdomain-enum-mcp — subfinder + amass + dnsx + crt.sh enumeration (§9.2).

When the native binaries are not available we fall back to certificate
transparency (crt.sh JSON) which gives a respectable subdomain list with
zero local tooling.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

import requests

from ._mcp_runtime import MCPServer

server = MCPServer(name="subdomain-enum-mcp")


def _native(tool: str, target: str) -> list[str]:
    bin_ = shutil.which(tool)
    if not bin_:
        return []
    try:
        if tool == "subfinder":
            cmd = [bin_, "-d", target, "-silent", "-all"]
        elif tool == "amass":
            cmd = [bin_, "enum", "-passive", "-d", target, "-norecursive"]
        elif tool == "dnsx":
            cmd = [bin_, "-d", target, "-silent", "-resp"]
        else:
            return []
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
    except Exception:  # noqa: BLE001
        return []


def _crtsh(target: str) -> list[str]:
    try:
        r = requests.get(f"https://crt.sh/?q=%25.{target}&output=json", timeout=20)
        if r.status_code != 200:
            return []
        out: set[str] = set()
        for row in r.json():
            for nv in str(row.get("name_value", "")).split("\n"):
                nv = nv.strip().lower().lstrip("*.")
                if nv.endswith(target):
                    out.add(nv)
        return sorted(out)
    except Exception:  # noqa: BLE001
        return []


@server.tool("enumerate", schema={"target": "string", "passive_only": "bool"})
def enumerate(target: str, passive_only: bool = True) -> dict[str, Any]:
    found: set[str] = set()
    sources: dict[str, int] = {}
    for tool in ("subfinder", "amass") if passive_only else ("subfinder", "amass", "dnsx"):
        results = _native(tool, target)
        sources[tool] = len(results)
        found.update(results)
    crtsh_results = _crtsh(target)
    sources["crtsh"] = len(crtsh_results)
    found.update(crtsh_results)
    return {"target": target, "sources": sources,
            "subdomains": sorted(found), "total": len(found)}


if __name__ == "__main__":
    server.serve_stdio()
