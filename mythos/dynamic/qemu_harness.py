"""QEMU full-system emulation harness for kernel-level fuzzing experiments."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any


class QEMUHarness:
    def __init__(self):
        self.bin = shutil.which("qemu-system-x86_64") or shutil.which("qemu-x86_64")

    def available(self) -> bool:
        return bool(self.bin)

    def run(self, harness_dir: str) -> list[dict[str, Any]]:
        if not self.available():
            return []
        # Look for prepared kernel images / userland binaries.
        kernels = [p for p in os.listdir(harness_dir) if p.endswith((".elf", ".bin"))]
        if not kernels:
            return []
        traces: list[dict[str, Any]] = []
        for kern in kernels:
            try:
                proc = subprocess.run(
                    [self.bin, "-d", "in_asm,exec", "-D", "/tmp/qemu.log",
                     "-no-reboot", "-nographic", "-kernel", os.path.join(harness_dir, kern)],
                    capture_output=True, text=True, timeout=120, check=False,
                )
                traces.append({"kernel": kern,
                               "stdout_tail": proc.stdout[-1500:],
                               "stderr_tail": proc.stderr[-1500:]})
            except subprocess.TimeoutExpired:
                traces.append({"kernel": kern, "error": "timeout"})
        return traces
