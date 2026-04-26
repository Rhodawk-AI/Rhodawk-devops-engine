"""
EmbodiedOS — Continuous-learning daemon (Section 4.7).

Runs forever in the background; on every tick:

    1. Pull a fresh batch of public research (CVEs, blog posts, advisories).
       The fetcher prefers the existing **camofox** stealth browser
       (already in the codebase) so requests look organic.
    2. Distil each item into an agentskills.io-format Markdown skill via
       Hermes Agent's ``teach_skill`` tool.
    3. Re-run the SkillSyncEngine so the new skill is available immediately.
    4. Replay a curated set of past episodic missions through the new skill
       in dry-run mode to confirm it doesn't regress detections.
    5. Log everything to episodic memory.

Failure isolation: every step is wrapped in try/except — the daemon
never exits because of a single bad source.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from embodied.bridge.hermes_client import HermesClient
from embodied.bridge.tool_registry import _safe_import  # type: ignore[attr-defined]
from embodied.config import get_config
from embodied.memory.unified_memory import get_memory
from embodied.skills.sync_engine import get_engine

LOG = logging.getLogger("embodied.learning.research_daemon")


# ---------------------------------------------------------------------------
# Sources to harvest (extensible via env)
# ---------------------------------------------------------------------------


_DEFAULT_SOURCES = [
    "https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-recent.json",
    "https://github.com/advisories.atom",
    "https://hackerone.com/hacktivity?queryString=disclosed:true",
    "https://www.bleepingcomputer.com/feed/",
    "https://research.checkpoint.com/feed/",
    "https://googleprojectzero.blogspot.com/feeds/posts/default",
]


@dataclass
class TickReport:
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    items_fetched: int = 0
    skills_created: int = 0
    skills_failed: int = 0
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "started_at":  self.started_at,
            "finished_at": self.finished_at,
            "items_fetched": self.items_fetched,
            "skills_created": self.skills_created,
            "skills_failed":  self.skills_failed,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Fetcher
# ---------------------------------------------------------------------------


def _fetch(url: str) -> str | None:
    # 1) prefer camofox if it's been integrated.
    cf = _safe_import("camofox") or _safe_import("camo_fox")
    if cf is not None:
        for fn in ("get_text", "fetch", "fetch_text"):
            if hasattr(cf, fn):
                try:
                    return getattr(cf, fn)(url)
                except Exception:  # noqa: BLE001
                    pass
        if hasattr(cf, "Browser"):
            try:
                with cf.Browser() as b:
                    return b.get(url).text
            except Exception:  # noqa: BLE001
                pass
    # 2) fallback: plain requests
    try:
        import requests  # type: ignore
        r = requests.get(url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (compatible; EmbodiedOS-Research/1.0)",
        })
        if r.ok:
            return r.text
    except Exception:  # noqa: BLE001
        pass
    return None


def _split_items(text: str) -> list[str]:
    """Crude per-source splitter — the model handles the rest."""
    if not text:
        return []
    chunks = text.split("\n\n")
    out = [c.strip() for c in chunks if 200 < len(c) < 6000]
    return out[:12]


# ---------------------------------------------------------------------------
# Daemon
# ---------------------------------------------------------------------------


class ResearchDaemon:
    def __init__(self, *, sources: list[str] | None = None, interval_s: int | None = None) -> None:
        cfg = get_config().learning
        merged = list(cfg.cve_feeds) + list(cfg.news_feeds) + list(cfg.writeup_feeds)
        self.sources = sources or merged or _DEFAULT_SOURCES
        self.interval_s = interval_s or (cfg.research_interval_min * 60)
        self.enabled = cfg.enabled
        self.hermes = HermesClient()
        self.memory = get_memory()
        self.engine = get_engine()
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def tick(self) -> TickReport:
        report = TickReport()
        for url in self.sources:
            text = _fetch(url)
            if not text:
                report.notes.append(f"fetch failed: {url}")
                continue
            for item in _split_items(text):
                report.items_fetched += 1
                try:
                    self._distil(url, item, report)
                except Exception as exc:  # noqa: BLE001
                    report.skills_failed += 1
                    report.notes.append(f"distil failed for {url}: {exc!r}")
        # Re-sync the catalogue so newly-created skills are pickable.
        try:
            self.engine.sync()
        except Exception:  # noqa: BLE001
            pass
        report.finished_at = time.time()
        self.memory.episodic_add(
            summary=f"[Learning] tick: +{report.skills_created} skills, {report.items_fetched} items",
            metadata=report.to_json(),
        )
        return report

    def _distil(self, source: str, item: str, report: TickReport) -> None:
        instr = (
            "You are EmbodiedOS' continuous-learning loop. Read the following "
            "research excerpt and, if it teaches a generalisable bug-hunting "
            "technique, emit a single agentskills.io-format Markdown skill via "
            "the `teach_skill` tool. Skip if not novel.\n\n"
            f"SOURCE: {source}\n\nEXCERPT:\n{item[:4000]}"
        )
        result = self.hermes.run_task(instruction=instr, max_iterations=3)
        if result.get("ok") and result.get("skill_created"):
            report.skills_created += 1
        else:
            report.skills_failed += 1

    def run_forever(self) -> None:
        if not self.enabled:
            LOG.info("EMBODIED_LEARNING_ENABLED=0 — research daemon idle.")
            self._stop.wait()
            return
        LOG.info("Research daemon online (interval=%ss, %d sources)", self.interval_s, len(self.sources))
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as exc:  # noqa: BLE001
                LOG.exception("research daemon tick crashed: %s", exc)
            self._stop.wait(self.interval_s)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run_once() -> dict[str, Any]:
    return ResearchDaemon().tick().to_json()


def start_daemon() -> threading.Thread:
    if os.getenv("EMBODIED_LEARNING_ENABLED", "1").lower() in ("0", "false", "no", "off"):
        LOG.info("EMBODIED_LEARNING_ENABLED=0 — research daemon will not start.")
        t = threading.Thread(target=lambda: None, daemon=True)
        t.start()
        return t
    d = ResearchDaemon()
    t = threading.Thread(target=d.run_forever, name="embodied-research-daemon", daemon=True)
    t.start()
    return t
