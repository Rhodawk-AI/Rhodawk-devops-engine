"""
EmbodiedOS — unified integration layer for Rhodawk DevSecOps Engine.

This package is **strictly additive**.  It does not modify, move, or replace
any existing module.  It glues three pre-existing systems into a single
"autonomous security researcher":

  1. The Rhodawk DevSecOps Engine (this repository) — all analysis engines,
     scanners, the OpenClaude bridge, the verification loop, the
     disclosure vault and the bounty gateway.
  2. Nous Research **Hermes Agent** (installed separately) — three-layer
     memory, nudge engine, subagent delegation, auto-skill creation and
     a 639+ community skill library.
  3. **OpenClaw** (installed separately) — multi-channel gateway
     (Telegram, Discord, Slack, WhatsApp, …), 13,000+ ClawHub skills,
     Chrome Relay browser automation and a cron/background job engine.

Every wrapper here degrades gracefully: a missing optional dependency or
an offline external agent never crashes a request — it returns a
structured ``{"ok": False, "reason": ...}`` response instead.

Public surface (re-exported for convenience):

    embodied.config         — central configuration (env-driven)
    embodied.bridge         — EmbodiedOS MCP server + agent clients
    embodied.router         — unified command + intent router
    embodied.pipelines      — Side 1 (repo hunter) / Side 2 (bounty hunter)
    embodied.skills         — Skill Sync Engine (3-pool unification)
    embodied.memory         — three-layer unified memory facade
    embodied.learning       — autonomous research daemon

Use ``python -m embodied --help`` to see the CLI surface.
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = [
    "config",
    "bridge",
    "router",
    "pipelines",
    "skills",
    "memory",
    "learning",
]
