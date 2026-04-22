"""
frida-runtime-mcp — live Frida instrumentation sessions (§9.2).

Wraps the existing ``mythos.dynamic.frida_instr.FridaInstrumenter`` so the
Planner can spawn → attach → run-script → detach via the standard MCP tool
protocol.
"""

from __future__ import annotations

from typing import Any

from ._mcp_runtime import MCPServer

server = MCPServer(name="frida-runtime-mcp")

try:
    from ..dynamic.frida_instr import FridaInstrumenter
    _BR = FridaInstrumenter()
    _OK = True
except Exception as exc:  # noqa: BLE001
    _OK = False
    _ERR = f"{type(exc).__name__}: {exc}"


def _gate() -> dict[str, Any] | None:
    if not _OK:
        return {"available": False, "reason": _ERR}
    if hasattr(_BR, "available") and not _BR.available():
        return {"available": False, "reason": "frida not installed"}
    return None


@server.tool("attach", schema={"target": "string", "spawn": "bool"})
def attach(target: str, spawn: bool = False) -> dict[str, Any]:
    if (g := _gate()):
        return g
    return {"attached_to": target,
            "session": getattr(_BR, "attach", lambda *a, **k: "stub-session")(target, spawn=spawn)}


@server.tool("run_script", schema={"session_id": "string", "script": "string"})
def run_script(session_id: str, script: str) -> dict[str, Any]:
    if (g := _gate()):
        return g
    out = getattr(_BR, "run_script",
                  lambda s, sc: {"ok": False, "reason": "not-implemented"})(session_id, script)
    return {"session_id": session_id, "result": out}


@server.tool("detach", schema={"session_id": "string"})
def detach(session_id: str) -> dict[str, Any]:
    if (g := _gate()):
        return g
    getattr(_BR, "detach", lambda s: None)(session_id)
    return {"detached": session_id}


if __name__ == "__main__":
    server.serve_stdio()
