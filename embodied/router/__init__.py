"""
EmbodiedOS — Unified Command Interface & Intent Router (Section 4.1).
"""

from __future__ import annotations

from .intent_router import (
    Intent,
    IntentMatch,
    IntentRouter,
    classify,
    default_router,
)
from .unified_gateway import UnifiedGateway, build_gateway, dispatch

__all__ = [
    "Intent",
    "IntentMatch",
    "IntentRouter",
    "classify",
    "default_router",
    "UnifiedGateway",
    "build_gateway",
    "dispatch",
]
