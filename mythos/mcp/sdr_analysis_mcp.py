"""
sdr-analysis-mcp — GNU Radio scripted RF analysis (§9.2 / §7 frontier).

Drives ``gr-fosphor`` / ``rtl_sdr`` / ``hackrf_transfer`` style binaries via
subprocess.  Without any SDR tooling on PATH every tool returns
``available=False``.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from typing import Any

from ._mcp_runtime import MCPServer

server = MCPServer(name="sdr-analysis-mcp")


def _have(b: str) -> bool:
    return shutil.which(b) is not None


@server.tool("capture_iq",
             schema={"freq_hz": "int", "sample_rate_hz": "int", "duration_s": "int"})
def capture_iq(freq_hz: int, sample_rate_hz: int = 2_400_000,
               duration_s: int = 5) -> dict[str, Any]:
    """Capture an IQ sample to a temp file. Returns metadata + path."""
    if _have("rtl_sdr"):
        f = tempfile.NamedTemporaryFile("wb", suffix=".iq", delete=False)
        f.close()
        cmd = ["rtl_sdr", "-f", str(freq_hz), "-s", str(sample_rate_hz),
               "-n", str(duration_s * sample_rate_hz), f.name]
        try:
            subprocess.run(cmd, capture_output=True, timeout=duration_s + 30)
            return {"backend": "rtl_sdr", "iq_path": f.name,
                    "freq_hz": freq_hz, "sample_rate_hz": sample_rate_hz,
                    "duration_s": duration_s}
        except Exception as exc:  # noqa: BLE001
            return {"backend": "rtl_sdr", "error": str(exc)}
    if _have("hackrf_transfer"):
        f = tempfile.NamedTemporaryFile("wb", suffix=".iq", delete=False); f.close()
        cmd = ["hackrf_transfer", "-r", f.name, "-f", str(freq_hz),
               "-s", str(sample_rate_hz)]
        try:
            subprocess.run(cmd, capture_output=True, timeout=duration_s + 30)
            return {"backend": "hackrf_transfer", "iq_path": f.name,
                    "freq_hz": freq_hz}
        except Exception as exc:  # noqa: BLE001
            return {"backend": "hackrf_transfer", "error": str(exc)}
    return {"available": False, "reason": "no SDR tool on PATH"}


@server.tool("run_grc_flowgraph", schema={"flowgraph_py": "string"})
def run_grc_flowgraph(flowgraph_py: str) -> dict[str, Any]:
    """Execute a generated GNU Radio flowgraph. Caller is responsible for
    sandboxing the script body."""
    if not _have("python3"):
        return {"available": False, "reason": "python3 not on PATH"}
    f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
    f.write(flowgraph_py); f.close()
    try:
        out = subprocess.run(["python3", f.name],
                             capture_output=True, text=True, timeout=120)
        return {"exit_code": out.returncode,
                "stdout_tail": out.stdout[-3000:],
                "stderr_tail": out.stderr[-1500:]}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


if __name__ == "__main__":
    server.serve_stdio()
