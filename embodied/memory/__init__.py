"""
EmbodiedOS — Unified Memory (Section 4.6).

Three-layer memory:

  * Session (in-process, ring buffer)         — last K events per mission.
  * Episodic (SQLite, full-text searchable)   — every campaign summary.
  * Procedural (skills + rhodawk.knowledge)   — the *durable* lessons.
"""

from __future__ import annotations

from .unified_memory import UnifiedMemory, get_memory

__all__ = ["UnifiedMemory", "get_memory"]
