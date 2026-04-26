"""
EmbodiedOS — Skill Sync Engine (Section 4.5).

Walks all three skill pools, normalises entries to the agentskills.io
schema, deduplicates by semantic fingerprint, and produces:

  * A unified Markdown index at ``${EMBODIED_SKILL_CACHE}/UNIFIED_SKILLS.md``.
  * A JSON catalogue at  ``${EMBODIED_SKILL_CACHE}/unified_skills.json``.
  * An ephemeral ``AGENTS.md``-style prompt for a specific task, packing
    only the top-N most relevant skills (so the LLM context stays small).

Auto-created skills (Hermes Agent's auto-skill output, or the Side 1 /
Side 2 pipelines distilling a successful campaign) are written back to
**both** ``architect/skills/embodied_auto/`` (for git versioning) and
``${HERMES_SKILLS_DIR}/embodied_auto/`` (for Hermes' own catalogue).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from embodied.config import get_config
from embodied.skills.normalizer import UnifiedSkill, normalize_skill

LOG = logging.getLogger("embodied.skills.sync_engine")


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class SyncReport:
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    sources_scanned: dict[str, int] = field(default_factory=dict)
    duplicates_dropped: int = 0
    total_unified: int = 0
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "started_at":  self.started_at,
            "finished_at": self.finished_at,
            "sources_scanned":   self.sources_scanned,
            "duplicates_dropped": self.duplicates_dropped,
            "total_unified": self.total_unified,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class SkillSyncEngine:
    def __init__(self) -> None:
        cfg = get_config()
        self.local_dir = cfg.skills.local_dir
        self.cache_dir = cfg.skills.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hermes_dir = cfg.hermes.skills_dir
        self.openclaw_dir = cfg.openclaw.skills_dir
        self._catalogue: dict[str, UnifiedSkill] = {}
        self._lock = threading.Lock()

    # ----- discovery -------------------------------------------------------

    def _walk(self, root: Path, source: str) -> Iterable[UnifiedSkill]:
        if not root or not root.exists():
            return []
        out: list[UnifiedSkill] = []
        for p in root.rglob("*.md"):
            if p.name.lower() in {"readme.md", "license.md"}:
                continue
            sk = normalize_skill(path=p, source=source)
            if sk is not None:
                out.append(sk)
        return out

    # ----- public sync -----------------------------------------------------

    def sync(self) -> SyncReport:
        report = SyncReport()
        unified: dict[str, UnifiedSkill] = {}

        for source, root in (
            ("rhodawk",  self.local_dir),
            ("hermes",   self.hermes_dir),
            ("openclaw", self.openclaw_dir),
        ):
            count = 0
            for sk in self._walk(root, source):
                count += 1
                key = sk.fingerprint
                existing = unified.get(key)
                if existing is None:
                    unified[key] = sk
                else:
                    # Deterministic precedence: rhodawk > hermes > openclaw.
                    rank = {"rhodawk": 3, "hermes": 2, "openclaw": 1}
                    if rank.get(sk.source, 0) > rank.get(existing.source, 0):
                        unified[key] = sk
                    report.duplicates_dropped += 1
            report.sources_scanned[source] = count

        report.total_unified = len(unified)
        report.finished_at = time.time()
        with self._lock:
            self._catalogue = unified
        self._write_index(unified)
        report.notes.append(f"Wrote {len(unified)} unified skills to {self.cache_dir}.")
        return report

    # ----- task-time selection --------------------------------------------

    def select_for_task(
        self,
        *,
        task_description: str,
        profile: dict[str, Any] | None = None,
        attack_phase: str = "",
        top_k: int | None = None,
    ) -> str:
        """Return an ephemeral prompt block packing the top-N relevant skills."""
        cfg = get_config().skills
        top_k = top_k or cfg.top_k_default
        with self._lock:
            if not self._catalogue:
                # cold-start: lazy sync
                self.sync()
            skills = list(self._catalogue.values())

        # 1) keyword overlap score
        words = _tokenise(task_description) | _tokenise(attack_phase)
        prof_terms: set[str] = set()
        for v in (profile or {}).values():
            if isinstance(v, list):
                prof_terms |= {str(x).lower() for x in v}
            elif isinstance(v, str):
                prof_terms.add(v.lower())
        words |= prof_terms

        scored: list[tuple[float, UnifiedSkill]] = []
        for sk in skills:
            score = 0.0
            text = (sk.name + " " + sk.domain + " " + " ".join(sk.tools) + " " + sk.body[:1024]).lower()
            for w in words:
                if w and w in text:
                    score += 1.0
            for k, vs in sk.triggers.items():
                for v in vs:
                    if v.lower() in prof_terms:
                        score += 1.5
                    if v.lower() in text:
                        score += 0.25
            if attack_phase and attack_phase.lower() in sk.name.lower():
                score += 2.0
            if score > 0:
                scored.append((score, sk))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [sk for _s, sk in scored[: top_k]]

        # 2) try the existing semantic skill_selector for a re-rank if available
        try:
            from architect import skill_selector  # type: ignore
            if hasattr(skill_selector, "select_for_task"):
                packed = skill_selector.select_for_task(
                    task_description,
                    repo_languages=list(prof_terms),
                    repo_tech_stack=list(prof_terms),
                    attack_phase=attack_phase or "static",
                    top_k=top_k,
                )
                if isinstance(packed, str) and packed.strip():
                    # blend: existing block + EmbodiedOS extras
                    extras = "\n\n".join(_render_skill(sk) for sk in top)
                    return packed + "\n\n" + extras
        except Exception:  # noqa: BLE001
            pass

        return "\n\n".join(_render_skill(sk) for sk in top) or "<skills/>"

    # ----- auto-skill creation back-sync ----------------------------------

    def save_auto_skill(self, *, name: str, frontmatter: dict[str, Any], body: str) -> dict[str, Any]:
        """Persist a new skill in the canonical agentskills.io format."""
        sk = UnifiedSkill(
            name=name,
            source="hermes",
            path=Path(self.local_dir / "embodied_auto" / f"{name}.md"),
            domain=str(frontmatter.get("domain", "auto")),
            triggers=frontmatter.get("triggers", {}) or {},
            tools=list(frontmatter.get("tools", []) or []),
            severity_focus=list(frontmatter.get("severity_focus", []) or []),
            version=str(frontmatter.get("version", "0.1.0")),
            license=str(frontmatter.get("license", "")),
            body=body,
        )
        results: dict[str, Any] = {}
        for target_dir in (self.local_dir / "embodied_auto", self.hermes_dir / "embodied_auto"):
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / f"{name}.md"
                target.write_text(sk.to_markdown())
                results[str(target_dir)] = "ok"
            except Exception as exc:  # noqa: BLE001
                results[str(target_dir)] = f"failed: {exc!r}"
        return {"ok": True, "saved": results}

    # ----- writers ---------------------------------------------------------

    def _write_index(self, unified: dict[str, UnifiedSkill]) -> None:
        json_path = self.cache_dir / "unified_skills.json"
        md_path = self.cache_dir / "UNIFIED_SKILLS.md"
        try:
            json_path.write_text(json.dumps(
                {"generated_at": int(time.time()), "skills": [sk.to_json() for sk in unified.values()]},
                indent=2))
        except Exception as exc:  # noqa: BLE001
            LOG.warning("could not write %s: %s", json_path, exc)
        try:
            md_path.write_text(_render_index(unified))
        except Exception as exc:  # noqa: BLE001
            LOG.warning("could not write %s: %s", md_path, exc)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _render_skill(sk: UnifiedSkill) -> str:
    return (
        f"<skill name=\"{sk.name}\" source=\"{sk.source}\" domain=\"{sk.domain}\">\n"
        f"{sk.body.strip()[:2400]}\n"
        f"</skill>"
    )


def _render_index(unified: dict[str, UnifiedSkill]) -> str:
    lines = ["# EmbodiedOS Unified Skills Catalogue", ""]
    by_source: dict[str, list[UnifiedSkill]] = {}
    for sk in unified.values():
        by_source.setdefault(sk.source, []).append(sk)
    for source, skills in sorted(by_source.items()):
        lines.append(f"## {source} ({len(skills)})")
        for sk in sorted(skills, key=lambda s: s.name):
            lines.append(f"- `{sk.name}` — {sk.domain}")
        lines.append("")
    return "\n".join(lines)


def _tokenise(text: str) -> set[str]:
    return {t for t in (text or "").lower().split() if len(t) > 2}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_ENGINE: SkillSyncEngine | None = None
_ENGINE_LOCK = threading.Lock()


def get_engine() -> SkillSyncEngine:
    global _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is None:
            _ENGINE = SkillSyncEngine()
        return _ENGINE
