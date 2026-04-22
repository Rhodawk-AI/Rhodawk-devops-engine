"""
ARCHITECT — superhuman autonomous security agent runtime.

This package is the *control plane* for the ARCHITECT masterplan.  It sits on
top of the existing Rhodawk + Mythos engines and adds:

  * A typed model-tier router (DeepSeek V3.2 / MiniMax M2.5 / Qwen3 / Claude / local).
  * A pluggable skill registry that matches SKILL.md files to a target profile.
  * An EmbodiedOS bridge that forwards findings to Telegram / OpenClaw / Hermes Agent.
  * The autonomous "night-mode" scheduler (the 18:00 → 08:00 bug-bounty loop).
  * An isolated sandbox manager for safe OSS-Guardian repo cloning.

Everything in this package is import-safe even when optional binaries
(playwright, subfinder, dnsx, pwntools, …) are missing — heavy bridges are
loaded lazily and degrade to ``available()=False`` rather than raising.
"""

from __future__ import annotations

ARCHITECT_VERSION = "1.0.0"

__all__ = [
    "ARCHITECT_VERSION",
    "model_router",
    "skill_registry",
    "embodied_bridge",
    "nightmode",
    "sandbox",
]
