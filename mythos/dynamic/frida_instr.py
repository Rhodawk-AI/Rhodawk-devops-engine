"""Frida dynamic instrumentation — attaches a generic syscall/cred tracer."""

from __future__ import annotations

import os
from typing import Any

try:  # pragma: no cover
    import frida  # type: ignore
    _FRIDA = True
except Exception:  # noqa: BLE001
    _FRIDA = False

# Minimal generic JS instrumentation script — interceptors are expanded by
# the orchestrator at call-site for kind-specific tracing.
_DEFAULT_SCRIPT = r"""
const interesting = ['open', 'execve', 'connect', 'recvfrom', 'mmap'];
interesting.forEach((name) => {
  try {
    const sym = Module.findExportByName(null, name);
    if (sym) Interceptor.attach(sym, {
      onEnter(args) { send({event: name, args: args.map(a => a.toString())}); }
    });
  } catch (e) {}
});
"""


class FridaInstrumenter:
    def available(self) -> bool:
        return _FRIDA

    def attach_all(self, harness_dir: str) -> list[dict[str, Any]]:
        if not _FRIDA:
            return []
        events: list[dict[str, Any]] = []

        def on_message(msg, _data):
            if msg.get("type") == "send":
                events.append(msg.get("payload", {}))

        device = frida.get_local_device()
        for proc in device.enumerate_processes():
            if not any(proc.name.startswith(b) for b in ("python", "node", "java")):
                continue
            try:
                session = device.attach(proc.pid)
                script = session.create_script(_DEFAULT_SCRIPT)
                script.on("message", on_message)
                script.load()
            except Exception:
                continue
        return events[:500]
