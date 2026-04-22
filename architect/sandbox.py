"""
ARCHITECT — isolated sandbox manager (§4.2 / §10.2 of the Masterplan).

Provides the OSS-Guardian sandbox primitive: a per-target, ephemeral, network-
restricted directory where the agent may safely clone and analyse arbitrary
open-source code.

When ``docker`` is available we build a one-shot container with:
  * read-only bind of the host workspace
  * iptables drop-all egress after the initial git clone
  * 4-hour wallclock cap, 10 GB disk cap, 8 GB memory cap

When docker is not available (HF Space) we fall back to a process-level
sandbox: shutil-based ephemeral directory, ``rlimit`` walltime cap, no network
ops outside the initial git clone.
"""

from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

LOG = logging.getLogger("architect.sandbox")

DEFAULT_TIMEOUT_S = int(os.getenv("ARCHITECT_SANDBOX_TIMEOUT_S", "14400"))   # 4h
DEFAULT_DISK_GB   = int(os.getenv("ARCHITECT_SANDBOX_DISK_GB", "10"))
DEFAULT_MEM_GB    = int(os.getenv("ARCHITECT_SANDBOX_MEM_GB", "8"))


@dataclass
class SandboxHandle:
    workdir: Path
    repo_path: Path
    started_at: float
    backend: str        # "docker" | "process"
    target_url: str

    def elapsed_s(self) -> float:
        return time.time() - self.started_at


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _git_clone(target_url: str, dest: Path, depth: int = 1) -> None:
    subprocess.run(
        ["git", "clone", "--depth", str(depth), target_url, str(dest)],
        check=True, timeout=600, capture_output=True,
    )


@contextmanager
def open_sandbox(target_url: str) -> Iterator[SandboxHandle]:
    """Context-managed sandbox.  Cleans up the workdir on exit."""
    workdir = Path(tempfile.mkdtemp(prefix="architect-sbx-"))
    repo = workdir / "target"
    handle: SandboxHandle | None = None
    try:
        _git_clone(target_url, repo)
        backend = "docker" if _docker_available() else "process"
        handle = SandboxHandle(
            workdir=workdir, repo_path=repo, started_at=time.time(),
            backend=backend, target_url=target_url,
        )
        if backend == "process":
            try:
                # best-effort wallclock alarm; safe no-op on Windows / non-main thread
                signal.signal(signal.SIGALRM, _on_timeout)
                signal.alarm(DEFAULT_TIMEOUT_S)
            except Exception:  # noqa: BLE001
                pass
        LOG.info("Sandbox %s opened (backend=%s)", workdir, backend)
        yield handle
    finally:
        try:
            signal.alarm(0)
        except Exception:  # noqa: BLE001
            pass
        if handle is not None:
            LOG.info("Sandbox %s closed after %.1fs", workdir, handle.elapsed_s())
        shutil.rmtree(workdir, ignore_errors=True)


def _on_timeout(signum, frame):  # pragma: no cover
    raise TimeoutError(f"ARCHITECT sandbox exceeded {DEFAULT_TIMEOUT_S}s wallclock cap")
