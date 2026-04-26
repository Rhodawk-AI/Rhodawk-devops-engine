"""
EmbodiedOS — central configuration.

All knobs are environment-driven so the bridge can be reconfigured without
touching code.  Defaults are chosen so that a developer running a fresh
clone can ``python -m embodied --help`` and get something usable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, "1" if default else "0").lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class HermesConfig:
    """Configuration for the Nous Research Hermes Agent."""

    base_url: str = field(default_factory=lambda: _env("HERMES_AGENT_URL", "http://127.0.0.1:8400"))
    api_key: str = field(default_factory=lambda: _env("HERMES_AGENT_API_KEY", ""))
    skills_dir: Path = field(
        default_factory=lambda: Path(_env("HERMES_SKILLS_DIR", str(Path.home() / ".hermes" / "skills")))
    )
    memory_dir: Path = field(
        default_factory=lambda: Path(_env("HERMES_MEMORY_DIR", str(Path.home() / ".hermes" / "memory")))
    )
    enabled: bool = field(default_factory=lambda: _env_bool("HERMES_ENABLED", True))


@dataclass(frozen=True)
class OpenClawConfig:
    """Configuration for the OpenClaw multi-channel gateway."""

    base_url: str = field(default_factory=lambda: _env("OPENCLAW_BASE_URL", "http://127.0.0.1:8500"))
    api_key: str = field(default_factory=lambda: _env("OPENCLAW_API_KEY", ""))
    skills_dir: Path = field(
        default_factory=lambda: Path(_env("OPENCLAW_SKILLS_DIR", str(Path.home() / ".openclaw" / "skills")))
    )
    chrome_relay_url: str = field(
        default_factory=lambda: _env("OPENCLAW_CHROME_RELAY_URL", "http://127.0.0.1:8501")
    )
    enabled: bool = field(default_factory=lambda: _env_bool("OPENCLAW_ENABLED", True))


@dataclass(frozen=True)
class BridgeConfig:
    """Configuration for the EmbodiedOS MCP bridge server itself."""

    host: str = field(default_factory=lambda: _env("EMBODIED_BRIDGE_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _env_int("EMBODIED_BRIDGE_PORT", 8600))
    transport: str = field(default_factory=lambda: _env("EMBODIED_BRIDGE_TRANSPORT", "http"))
    shared_secret: str = field(default_factory=lambda: _env("EMBODIED_BRIDGE_SECRET", ""))


@dataclass(frozen=True)
class SkillsConfig:
    """Configuration for the Skill Sync Engine."""

    local_dir: Path = field(
        default_factory=lambda: Path(_env("ARCHITECT_SKILLS_DIR", str(Path(__file__).resolve().parents[1] / "architect" / "skills")))
    )
    sync_interval_min: int = field(default_factory=lambda: _env_int("EMBODIED_SKILL_SYNC_MIN", 60))
    top_k_default: int = field(default_factory=lambda: _env_int("EMBODIED_SKILL_TOPK", 12))
    cache_dir: Path = field(
        default_factory=lambda: Path(_env("EMBODIED_SKILL_CACHE", "/tmp/embodied_skill_cache"))
    )


@dataclass(frozen=True)
class MemoryConfig:
    """Configuration for the unified three-layer memory."""

    session_dir: Path = field(
        default_factory=lambda: Path(_env("EMBODIED_SESSION_DIR", "/tmp/embodied_session"))
    )
    episodic_db: Path = field(
        default_factory=lambda: Path(_env("EMBODIED_EPISODIC_DB", "/data/embodied_episodic.sqlite"))
    )
    procedural_dir: Path = field(
        default_factory=lambda: Path(_env("EMBODIED_PROCEDURAL_DIR", "/data/embodied_procedural"))
    )


@dataclass(frozen=True)
class LearningConfig:
    """Configuration for the autonomous continuous-learning daemon."""

    research_interval_min: int = field(default_factory=lambda: _env_int("EMBODIED_RESEARCH_MIN", 30))
    cve_feeds: tuple[str, ...] = (
        "https://cve.mitre.org/data/downloads/allitems.csv",
        "https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-recent.json.gz",
    )
    news_feeds: tuple[str, ...] = (
        "https://thehackernews.com/feeds/posts/default",
        "https://www.bleepingcomputer.com/feed/",
        "https://feeds.feedburner.com/PortSwigger",
    )
    writeup_feeds: tuple[str, ...] = (
        "https://hackerone.com/hacktivity",
        "https://infosecwriteups.com/feed",
    )
    enabled: bool = field(default_factory=lambda: _env_bool("EMBODIED_LEARNING_ENABLED", True))


@dataclass(frozen=True)
class EmbodiedConfig:
    hermes: HermesConfig = field(default_factory=HermesConfig)
    openclaw: OpenClawConfig = field(default_factory=OpenClawConfig)
    bridge: BridgeConfig = field(default_factory=BridgeConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    learning: LearningConfig = field(default_factory=LearningConfig)


_CACHED: EmbodiedConfig | None = None


def get_config() -> EmbodiedConfig:
    """Process-wide cached configuration accessor."""
    global _CACHED
    if _CACHED is None:
        _CACHED = EmbodiedConfig()
    return _CACHED


def reload_config() -> EmbodiedConfig:
    """Force a re-read of the environment (used by tests)."""
    global _CACHED
    _CACHED = EmbodiedConfig()
    return _CACHED
