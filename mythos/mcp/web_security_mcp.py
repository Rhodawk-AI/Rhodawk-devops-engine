"""
``web-security-mcp`` — bridges OWASP ZAP / sqlmap / nuclei.

When the binary isn't on ``$PATH`` we return a structured "unavailable"
result so the agent can fall back to the existing ``web-security-mcp``
heuristics in ``mcp_config.json``.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

from ._mcp_runtime import MCPServer

server = MCPServer("web-security-mcp")


def _runtool(cmd: list[str], timeout: int = 120) -> dict[str, Any]:
    if not shutil.which(cmd[0]):
        return {"available": False, "tool": cmd[0]}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, check=False)
        return {"available": True, "rc": proc.returncode,
                "stdout_tail": proc.stdout[-2000:],
                "stderr_tail": proc.stderr[-2000:]}
    except subprocess.TimeoutExpired:
        return {"available": True, "error": "timeout"}


@server.tool("zap_baseline", {"target": "string"})
def zap_baseline(target: str):
    return _runtool(["zap-baseline.py", "-t", target, "-q"], timeout=600)


@server.tool("nuclei_scan", {"target": "string", "templates": "string"})
def nuclei_scan(target: str, templates: str = ""):
    cmd = ["nuclei", "-u", target, "-jsonl", "-silent"]
    if templates:
        cmd += ["-t", templates]
    return _runtool(cmd, timeout=600)


@server.tool("sqlmap_quick", {"target": "string"})
def sqlmap_quick(target: str):
    return _runtool(["sqlmap", "-u", target, "--batch", "--level=2", "--risk=2"],
                    timeout=600)


if __name__ == "__main__":  # pragma: no cover
    server.serve_stdio()
