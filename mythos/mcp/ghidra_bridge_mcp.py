"""
ghidra-bridge-mcp — headless Ghidra analysis via subprocess (§9.2).

Uses ``analyzeHeadless`` so a GUI is never required.  Falls back to ``r2``
(radare2) if Ghidra is unavailable, and to ``readelf`` / ``objdump`` if
neither is present.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Any

from ._mcp_runtime import MCPServer

server = MCPServer(name="ghidra-bridge-mcp")


def _have(b: str) -> bool:
    return shutil.which(b) is not None


@server.tool("analyse_binary", schema={"binary_path": "string", "script": "string (optional)"})
def analyse_binary(binary_path: str, script: str = "") -> dict[str, Any]:
    if not os.path.isfile(binary_path):
        return {"error": "binary not found"}
    headless = shutil.which("analyzeHeadless")
    if headless:
        with tempfile.TemporaryDirectory() as proj:
            cmd = [headless, proj, "ARCHITECT_PROJ",
                   "-import", binary_path, "-deleteProject", "-scriptPath", proj]
            if script:
                script_path = os.path.join(proj, "user.py")
                with open(script_path, "w") as fh:
                    fh.write(script)
                cmd.extend(["-postScript", "user.py"])
            try:
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
                return {"backend": "ghidra-headless",
                        "exit_code": out.returncode,
                        "stdout_tail": out.stdout[-4000:],
                        "stderr_tail": out.stderr[-2000:]}
            except subprocess.TimeoutExpired:
                return {"backend": "ghidra-headless", "error": "timeout"}
    if _have("r2"):
        try:
            out = subprocess.run(
                ["r2", "-q", "-c", "aaa; afl; iI; ii; iz", binary_path],
                capture_output=True, text=True, timeout=120,
            )
            return {"backend": "radare2", "stdout": out.stdout[:8000]}
        except Exception as exc:  # noqa: BLE001
            return {"backend": "radare2", "error": str(exc)}
    if _have("readelf"):
        out = subprocess.run(["readelf", "-aW", binary_path],
                             capture_output=True, text=True, timeout=60)
        return {"backend": "readelf", "stdout": out.stdout[:6000]}
    return {"available": False, "reason": "no binary-analysis backend on PATH"}


@server.tool("strings", schema={"binary_path": "string", "min_len": "int"})
def strings(binary_path: str, min_len: int = 6) -> dict[str, Any]:
    if not _have("strings"):
        return {"available": False}
    out = subprocess.run(["strings", "-n", str(min_len), binary_path],
                         capture_output=True, text=True, timeout=60)
    lines = out.stdout.splitlines()
    return {"count": len(lines), "sample": lines[:300]}


if __name__ == "__main__":
    server.serve_stdio()
