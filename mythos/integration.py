"""
Integration shim between the legacy ``hermes_orchestrator`` six-phase
pipeline and the new Mythos multi-agent framework.

The shim is *additive*: existing Rhodawk code paths keep working unchanged.
Callers that opt in to Mythos by setting ``RHODAWK_MYTHOS=1`` get the
Planner/Explorer/Executor pipeline transparently.
"""

from __future__ import annotations

import os
from typing import Any


def mythos_enabled() -> bool:
    return os.getenv("RHODAWK_MYTHOS", "0").lower() in ("1", "true", "yes", "on")


def maybe_run_mythos(target: dict[str, Any]) -> dict[str, Any] | None:
    """If Mythos is enabled, run the multi-agent pipeline and return its dossier."""
    if not mythos_enabled():
        return None
    from .agents.orchestrator import MythosOrchestrator

    orch = MythosOrchestrator()
    return orch.run_campaign(target)
