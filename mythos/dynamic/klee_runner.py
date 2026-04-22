"""KLEE symbolic execution runner — emits per-path execution traces."""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
from typing import Any


class KLEERunner:
    def __init__(self, time_budget_s: int = 120):
        self.bin = shutil.which("klee")
        self.time_budget_s = int(os.getenv("MYTHOS_KLEE_BUDGET", time_budget_s))

    def available(self) -> bool:
        return bool(self.bin)

    def run(self, harness_dir: str) -> list[dict[str, Any]]:
        if not self.available() or not os.path.isdir(harness_dir):
            return []
        traces: list[dict[str, Any]] = []
        for bc in glob.glob(os.path.join(harness_dir, "*.bc")):
            try:
                proc = subprocess.run(
                    [self.bin, "--max-time", str(self.time_budget_s), bc],
                    capture_output=True, text=True, timeout=self.time_budget_s + 30, check=False,
                )
                traces.append({
                    "module": bc,
                    "stdout_tail": proc.stdout[-2000:],
                    "stderr_tail": proc.stderr[-2000:],
                })
            except subprocess.TimeoutExpired:
                traces.append({"module": bc, "error": "timeout"})
        return traces
