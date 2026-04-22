"""
ARCHITECT — skill registry (§7 of the Masterplan).

Loads ``SKILL.md`` files from ``architect/skills/`` and ``/data/skills/``
(if present), parses their YAML front-matter, and exposes a ``match(profile)``
selector that returns the relevant skills for a given target profile.

The agentskills.io front-matter we expect:

    ---
    name: web-security-advanced
    domain: web
    triggers:
      languages:    [python, javascript, typescript, php]
      frameworks:   [flask, fastapi, django, express, rails]
      asset_types:  [http, web]
    tools:          [burp, ffuf, nuclei, sqlmap]
    severity_focus: [P1, P2]
    ---
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LOG = logging.getLogger("architect.skill_registry")

DEFAULT_SKILLS_DIR = Path(__file__).resolve().parent / "skills"
RUNTIME_SKILLS_DIR = Path(os.getenv("ARCHITECT_SKILLS_DIR", "/data/skills"))


@dataclass
class Skill:
    name: str
    path: Path
    domain: str = "general"
    triggers: dict[str, list[str]] = field(default_factory=dict)
    tools: list[str] = field(default_factory=list)
    severity_focus: list[str] = field(default_factory=list)
    body: str = ""

    def matches(self, profile: dict[str, Any]) -> int:
        """Return a positive match score; 0 means 'do not load'."""
        score = 0
        for key, wanted in self.triggers.items():
            present = profile.get(key) or []
            if isinstance(present, str):
                present = [present]
            for w in wanted:
                if w.lower() in (str(p).lower() for p in present):
                    score += 1
        return score


def _parse(path: Path) -> Skill | None:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        LOG.warning("Could not read skill %s: %s", path, exc)
        return None
    m = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    meta: dict[str, Any] = {"name": path.stem}
    body = text
    if m:
        body = m.group(2)
        for line in m.group(1).splitlines():
            if ":" not in line:
                continue
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if v.startswith("[") and v.endswith("]"):
                meta[k] = [x.strip() for x in v[1:-1].split(",") if x.strip()]
            else:
                meta[k] = v
        # nested triggers block
        trigger_block = re.search(r"^triggers:\s*\n((?:\s+.*\n?)+)", m.group(1), re.MULTILINE)
        if trigger_block:
            triggers: dict[str, list[str]] = {}
            for line in trigger_block.group(1).splitlines():
                m2 = re.match(r"\s+(\w+):\s*\[(.*?)\]", line)
                if m2:
                    triggers[m2.group(1)] = [x.strip() for x in m2.group(2).split(",") if x.strip()]
            if triggers:
                meta["triggers"] = triggers
    return Skill(
        name=str(meta.get("name", path.stem)),
        path=path,
        domain=str(meta.get("domain", "general")),
        triggers=meta.get("triggers", {}) if isinstance(meta.get("triggers"), dict) else {},
        tools=meta.get("tools", []) if isinstance(meta.get("tools"), list) else [],
        severity_focus=meta.get("severity_focus", []) if isinstance(meta.get("severity_focus"), list) else [],
        body=body,
    )


def load_all() -> list[Skill]:
    skills: list[Skill] = []
    for root in (DEFAULT_SKILLS_DIR, RUNTIME_SKILLS_DIR):
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.md")):
            s = _parse(p)
            if s:
                skills.append(s)
    LOG.info("Skill registry loaded %d skills", len(skills))
    return skills


def match(profile: dict[str, Any], top_k: int = 6) -> list[Skill]:
    scored = [(s.matches(profile), s) for s in load_all()]
    scored.sort(key=lambda t: t[0], reverse=True)
    return [s for sc, s in scored if sc > 0][:top_k]


def render_skill_pack(profile: dict[str, Any], top_k: int = 6) -> str:
    """Materialise the matched skills as a single markdown pack ready to paste
    into a system prompt."""
    chosen = match(profile, top_k=top_k)
    if not chosen:
        return "# No domain-specific skills matched. Operating with general training only.\n"
    parts = [f"# ARCHITECT skill pack ({len(chosen)} skill(s))\n",
             f"# Profile: {profile}\n"]
    for s in chosen:
        parts.append(f"\n---\n## skill::{s.name} (domain={s.domain})\n")
        parts.append(s.body.strip())
    return "\n".join(parts)


def stats() -> dict[str, Any]:
    skills = load_all()
    return {
        "total": len(skills),
        "by_domain": {d: sum(1 for s in skills if s.domain == d)
                      for d in sorted({s.domain for s in skills})},
        "default_dir": str(DEFAULT_SKILLS_DIR),
        "runtime_dir": str(RUNTIME_SKILLS_DIR),
    }
