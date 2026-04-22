"""
Rhodawk Mythos-Level Upgrade Package
=====================================

This package implements the "Ascending to Mythos-Level" blueprint
(see ``mythos/MYTHOS_PLAN.md``) on top of the existing Rhodawk
EmbodiedOS / Hermes orchestration core.

Layout
------

mythos/
├── MYTHOS_PLAN.md                  – the living plan (source of truth)
├── agents/                         – Planner / Explorer / Executor + orchestrator
├── reasoning/                      – probabilistic hypothesis engine + attack graphs
├── static/                         – Tree-sitter, Joern, CodeQL, Semgrep bridges
├── dynamic/                        – AFL++, KLEE, QEMU, Frida, GDB automation
├── exploit/                        – Pwntools / ROPGadget / heap / privesc kits
├── learning/                       – RL planner, MLflow tracker, LoRA, curriculum, episodic memory
├── mcp/                            – static / dynamic / exploit / vuln-db / web-security MCP servers
├── api/                            – FastAPI productization layer
└── skills/                         – agentskills.io standardised skill registry

Every concrete module degrades gracefully when its optional native
dependency (Joern, KLEE, AFL++, Frida, Pyro, …) is missing — Mythos
modules detect the absence and either fall back to a pure-Python heuristic
or raise a clean ``MythosToolUnavailable`` so the orchestrator can route
around the missing capability.
"""

from __future__ import annotations

__all__ = [
    "MythosToolUnavailable",
    "MYTHOS_VERSION",
    "build_default_orchestrator",
]

MYTHOS_VERSION = "1.0.0"


class MythosToolUnavailable(RuntimeError):
    """Raised when an optional native tool (Joern, KLEE, AFL++, ...) is missing."""


def build_default_orchestrator(**kwargs):
    """Convenience constructor — defers heavy imports until first call."""
    from .agents.orchestrator import MythosOrchestrator

    return MythosOrchestrator(**kwargs)
