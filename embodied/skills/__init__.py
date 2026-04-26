"""
EmbodiedOS — Skill Sync Engine (Section 4.5).

Unifies three skill pools (architect/skills, ~/.hermes/skills, ~/.openclaw/skills)
into a single normalised, deduplicated, semantically-rankable catalogue.
"""

from __future__ import annotations

from .normalizer import (
    AGENTSKILLS_KEYS,
    UnifiedSkill,
    normalize_skill,
    parse_markdown_with_frontmatter,
)
from .sync_engine import SkillSyncEngine, SyncReport, get_engine

__all__ = [
    "AGENTSKILLS_KEYS",
    "UnifiedSkill",
    "normalize_skill",
    "parse_markdown_with_frontmatter",
    "SkillSyncEngine",
    "SyncReport",
    "get_engine",
]
