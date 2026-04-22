"""
AFL++ runner.

If ``afl-fuzz`` is on ``$PATH`` we drive a short, time-boxed campaign over
each harness directory.  Otherwise we route through the existing
``fuzzing_engine`` (Hypothesis-based) so the orchestrator still produces
crash candidates.
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import time
from typing import Any


class AFLPlusPlusRunner:
    def __init__(self, time_budget_s: int = 60):
        self.bin = shutil.which("afl-fuzz")
        self.time_budget_s = int(os.getenv("MYTHOS_AFL_BUDGET", time_budget_s))

    def available(self) -> bool:
        return bool(self.bin)

    def run(self, harness_dir: str) -> list[dict[str, Any]]:
        if not os.path.isdir(harness_dir):
            return []
        if not self.available():
            return self._hypothesis_fallback(harness_dir)
        crashes: list[dict[str, Any]] = []
        for harness in glob.glob(os.path.join(harness_dir, "*_harness")):
            in_dir = os.path.join(harness_dir, "afl_in")
            out_dir = os.path.join(harness_dir, f"afl_out_{os.path.basename(harness)}")
            os.makedirs(in_dir, exist_ok=True)
            if not os.listdir(in_dir):
                with open(os.path.join(in_dir, "seed"), "wb") as fh:
                    fh.write(b"A" * 16)
            os.makedirs(out_dir, exist_ok=True)
            try:
                start = time.time()
                proc = subprocess.Popen(
                    [self.bin, "-i", in_dir, "-o", out_dir, "-V", str(self.time_budget_s),
                     "--", harness, "@@"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                proc.wait(timeout=self.time_budget_s + 30)
                for crash_path in glob.glob(os.path.join(out_dir, "default", "crashes", "id:*")):
                    crashes.append({
                        "id": os.path.basename(crash_path),
                        "harness": harness,
                        "path": crash_path,
                        "elapsed_s": round(time.time() - start, 2),
                        "signature": self._signature(crash_path),
                    })
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        return crashes

    @staticmethod
    def _signature(path: str) -> str:
        try:
            with open(path, "rb") as fh:
                return fh.read(64).hex()
        except OSError:
            return ""

    @staticmethod
    def _hypothesis_fallback(harness_dir: str) -> list[dict[str, Any]]:
        """Surface a marker that the legacy fuzzing_engine will consume."""
        marker = os.path.join(harness_dir, "_mythos_afl_unavailable.json")
        try:
            with open(marker, "w") as fh:
                json.dump({"fallback": "hypothesis"}, fh)
        except OSError:
            pass
        return []
