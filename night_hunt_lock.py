"""
Rhodawk AI — Night Hunt Mutual Exclusion Lock
==============================================
Resolves W-009 (MEDIUM): two entirely separate autonomous bug-bounty hunting
systems exist (`night_hunt_orchestrator.py` and `architect/nightmode.py`). Both
can be enabled simultaneously and both scan the same bounty platform scope
(HackerOne, Bugcrowd, Intigriti) with no deduplication or coordination.

This module exposes a single in-process re-entrant lock that BOTH orchestrators
must acquire before running a hunt cycle. Whichever loop wakes up first holds
the lock for the duration of its cycle; the other simply skips this round and
sleeps until its next scheduled wake.

Cross-process protection (multi-container deployments) should layer a
SQLite/Postgres advisory lock on top of this, but for the single-container HF
Spaces deployment the in-process lock is sufficient.

Usage:

    from night_hunt_lock import try_acquire_night_hunt, release_night_hunt

    if not try_acquire_night_hunt("architect-nightmode"):
        LOG.info("another night-hunt loop is already running; skipping cycle")
        return
    try:
        run_one_cycle()
    finally:
        release_night_hunt("architect-nightmode")

Or as a context manager:

    from night_hunt_lock import night_hunt_guard
    with night_hunt_guard("night-hunt-orchestrator") as acquired:
        if not acquired:
            return
        run_night_cycle()
"""

from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager

# Operators may opt out of the cross-loop guard if they truly want both
# loops to run independently (not recommended). Default: enabled.
_ENABLED = os.getenv("RHODAWK_NIGHT_HUNT_LOCK", "true").lower() == "true"

_LOCK = threading.Lock()
_HOLDER: str | None = None
_ACQUIRED_AT: float = 0.0


def is_locked() -> tuple[bool, str | None, float]:
    """Return (locked, holder_name, seconds_held)."""
    with _LOCK:
        if _HOLDER is None:
            return (False, None, 0.0)
        return (True, _HOLDER, time.time() - _ACQUIRED_AT)


def try_acquire_night_hunt(holder: str) -> bool:
    """Non-blocking acquire. Returns True if this caller now owns the lock."""
    global _HOLDER, _ACQUIRED_AT
    if not _ENABLED:
        return True
    with _LOCK:
        if _HOLDER is not None:
            return False
        _HOLDER = holder
        _ACQUIRED_AT = time.time()
        return True


def release_night_hunt(holder: str) -> None:
    """Release the lock. Only the current holder may release."""
    global _HOLDER, _ACQUIRED_AT
    if not _ENABLED:
        return
    with _LOCK:
        if _HOLDER == holder:
            _HOLDER = None
            _ACQUIRED_AT = 0.0


@contextmanager
def night_hunt_guard(holder: str):
    """Context manager that yields True if the lock was acquired."""
    acquired = try_acquire_night_hunt(holder)
    try:
        yield acquired
    finally:
        if acquired:
            release_night_hunt(holder)
