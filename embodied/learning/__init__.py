"""
EmbodiedOS — Continuous learning daemon (Section 4.7).
"""

from __future__ import annotations

from .research_daemon import ResearchDaemon, run_once, start_daemon

__all__ = ["ResearchDaemon", "run_once", "start_daemon"]
