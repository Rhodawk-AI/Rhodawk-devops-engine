"""
GDB-Python automation — replays a crash through GDB and captures
backtrace, registers, and a small chunk of memory around the crash site.

When GDB is missing the function returns a structured marker so the
orchestrator can record the gap.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Any

_GDB_SCRIPT = """\
set pagination off
set logging file {logfile}
set logging on
run < {input}
bt
info registers
x/64x $sp
quit
"""


class GDBAutomation:
    def __init__(self):
        self.bin = shutil.which("gdb")

    def available(self) -> bool:
        return bool(self.bin)

    def replay(self, crash: dict[str, Any]) -> dict[str, Any]:
        if not self.available():
            return {"crash": crash.get("id"), "gdb": "unavailable"}
        binary = crash.get("harness")
        crash_input = crash.get("path")
        if not (binary and crash_input and os.path.exists(binary) and os.path.exists(crash_input)):
            return {"crash": crash.get("id"), "gdb": "missing-binary-or-input"}
        with tempfile.TemporaryDirectory() as work:
            logfile = os.path.join(work, "gdb.log")
            scriptfile = os.path.join(work, "script.gdb")
            with open(scriptfile, "w") as fh:
                fh.write(_GDB_SCRIPT.format(logfile=logfile, input=crash_input))
            try:
                subprocess.run([self.bin, "-q", "-batch", "-x", scriptfile, binary],
                               capture_output=True, timeout=60, check=False)
                with open(logfile) as fh:
                    log = fh.read()[-4000:]
            except Exception as exc:  # noqa: BLE001
                log = f"gdb error: {exc}"
            return {"crash": crash.get("id"), "gdb_log": log}
