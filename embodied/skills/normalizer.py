"""
EmbodiedOS — Skill normaliser (agentskills.io format).

The agentskills.io schema we standardise on:

    ---
    name:           string                    (required, unique)
    domain:         string                    (e.g. web | binary | mobile | infra)
    triggers:                                 (block matched by skill_registry)
        languages:   [string]
        frameworks:  [string]
        asset_types: [string]                 (repo | http | binary | api | …)
    tools:          [string]
    severity_focus: [string]                  ([P1, P2] etc.)
    source:         string                    (provenance: rhodawk | hermes | openclaw | claude-md)
    version:        string                    (free-form)
    license:        string
    ---
    <Markdown body>

The normaliser accepts the slightly-different shapes used by Hermes Agent
(``capabilities`` instead of ``triggers``) and OpenClaw (``inputs`` /
``outputs``) and rewrites them into the canonical schema above.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LOG = logging.getLogger("embodied.skills.normalizer")

AGENTSKILLS_KEYS = (
    "name", "domain", "triggers", "tools", "severity_focus",
    "source", "version", "license",
)


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class UnifiedSkill:
    name: str
    source: str                                   # rhodawk | hermes | openclaw | claude-md
    path: Path
    domain: str = "general"
    triggers: dict[str, list[str]] = field(default_factory=dict)
    tools: list[str] = field(default_factory=list)
    severity_focus: list[str] = field(default_factory=list)
    version: str = "0.0.0"
    license: str = ""
    body: str = ""
    fingerprint: str = ""

    def to_frontmatter(self) -> str:
        lines = ["---"]
        lines.append(f"name: {self.name}")
        lines.append(f"domain: {self.domain}")
        if self.triggers:
            lines.append("triggers:")
            for k, vs in self.triggers.items():
                lines.append(f"  {k}: [{', '.join(vs)}]")
        if self.tools:
            lines.append(f"tools: [{', '.join(self.tools)}]")
        if self.severity_focus:
            lines.append(f"severity_focus: [{', '.join(self.severity_focus)}]")
        lines.append(f"source: {self.source}")
        lines.append(f"version: {self.version}")
        if self.license:
            lines.append(f"license: {self.license}")
        lines.append("---")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        return f"{self.to_frontmatter()}\n\n{self.body.strip()}\n"

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "path": str(self.path),
            "domain": self.domain,
            "triggers": self.triggers,
            "tools": self.tools,
            "severity_focus": self.severity_focus,
            "version": self.version,
            "license": self.license,
            "fingerprint": self.fingerprint,
        }


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)", re.DOTALL)


def parse_markdown_with_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return ``(metadata, body)``. Metadata is a flat dict; ``triggers`` may be nested."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw_meta, body = m.group(1), m.group(2)
    meta: dict[str, Any] = {}
    current_block: str | None = None
    block: dict[str, Any] = {}
    for line in raw_meta.splitlines():
        if not line.strip():
            continue
        if not line.startswith(" ") and ":" in line:
            if current_block:
                meta[current_block] = block
                block = {}
                current_block = None
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if not val:
                current_block = key
                continue
            meta[key] = _coerce(val)
        elif current_block and ":" in line:
            k, _, v = line.strip().partition(":")
            block[k.strip()] = _coerce(v.strip())
    if current_block:
        meta[current_block] = block
    return meta, body


def _coerce(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        return [s.strip() for s in value[1:-1].split(",") if s.strip()]
    return value


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------


def normalize_skill(*, path: Path, source: str) -> UnifiedSkill | None:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        LOG.info("normaliser: cannot read %s: %s", path, exc)
        return None

    meta, body = parse_markdown_with_frontmatter(text)
    name = str(meta.get("name") or path.stem)

    # Hermes / Claude variants — rewrite to the canonical keys.
    triggers = meta.get("triggers")
    if not triggers and "capabilities" in meta:
        caps = meta.get("capabilities")
        if isinstance(caps, dict):
            triggers = caps
        elif isinstance(caps, list):
            triggers = {"asset_types": caps}
    if not triggers and "inputs" in meta:
        triggers = {"asset_types": meta.get("inputs", [])}
    triggers = triggers or {}

    tools = meta.get("tools") or meta.get("requires") or []
    if isinstance(tools, str):
        tools = [tools]

    severity = meta.get("severity_focus") or meta.get("severity") or []
    if isinstance(severity, str):
        severity = [severity]

    skill = UnifiedSkill(
        name=name,
        source=source,
        path=path,
        domain=str(meta.get("domain", "general")),
        triggers={str(k): list(v) if isinstance(v, list) else [str(v)] for k, v in triggers.items()},
        tools=list(tools),
        severity_focus=list(severity),
        version=str(meta.get("version", "0.0.0")),
        license=str(meta.get("license", "")),
        body=body,
    )
    skill.fingerprint = _fingerprint(skill)
    return skill


def _fingerprint(skill: UnifiedSkill) -> str:
    """Stable fingerprint used for semantic-similarity dedup."""
    h = hashlib.sha256()
    h.update(skill.name.lower().encode())
    h.update(b"|")
    h.update(skill.domain.lower().encode())
    h.update(b"|")
    body = re.sub(r"\s+", " ", skill.body or "").strip().lower()[:2048]
    h.update(body.encode())
    return h.hexdigest()
