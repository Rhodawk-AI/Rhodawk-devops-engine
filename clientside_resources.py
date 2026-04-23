"""
clientside_resources.py
───────────────────────
Programmatic access to the vendored
``zomasec/client-side-bugs-resources`` knowledge pack
(``vendor/clientside_bugs/RESOURCES.md``).

The upstream repo is a single, lovingly-curated README of links + reading
material for client-side bug hunting (XSS, postMessage, CSP, CORS,
prototype pollution, DOM internals, …).  Inside Rhodawk we want to:

  * Surface the resources as structured records the orchestrator can
    quote when triaging client-side findings.
  * Feed seed URLs into ``knowledge_rag.py`` so the embedding store gets
    real-world write-ups rather than only Rhodawk's own runs.
  * Provide a category → links lookup for ``red_team_fuzzer.py`` when it
    needs a quick reminder of what tradecraft exists for a given
    sub-class (e.g. ``"prototype_pollution"`` → 3 reference links).

Pure stdlib, zero side effects at import time apart from an `lru_cache`d
markdown parse.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger("rhodawk.clientside")

_HERE = Path(__file__).resolve().parent
RESOURCES_PATH = Path(
    os.environ.get(
        "RHODAWK_CLIENTSIDE_RESOURCES",
        str(_HERE / "vendor" / "clientside_bugs" / "RESOURCES.md"),
    )
)


# ─── Data model ────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Resource:
    title: str
    url: str
    section: str

    def to_dict(self) -> Dict[str, str]:
        return {"title": self.title, "url": self.url, "section": self.section}


# ─── Parser ────────────────────────────────────────────────────────────
_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")


def _read() -> str:
    try:
        return RESOURCES_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        log.warning("clientside resources missing at %s: %s", RESOURCES_PATH, exc)
        return ""


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


@lru_cache(maxsize=1)
def load() -> Dict[str, List[Resource]]:
    """Return ``{section_slug: [Resource, ...]}`` parsed from the README."""
    text = _read()
    if not text:
        return {}

    sections: Dict[str, List[Resource]] = {}
    current_section = "general"

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        # Section heading: ## Title  or  ### Title
        m_head = re.match(r"^#{2,3}\s+(.*)", line)
        if m_head:
            current_section = _slug(m_head.group(1))
            sections.setdefault(current_section, [])
            continue

        for title, url in _LINK_RE.findall(line):
            sections.setdefault(current_section, []).append(
                Resource(title=title.strip(), url=url.strip(), section=current_section)
            )

    return {k: v for k, v in sections.items() if v}


# ─── Public API ────────────────────────────────────────────────────────
def list_sections() -> List[str]:
    return sorted(load().keys())


def get_section(section: str) -> List[Resource]:
    return list(load().get(_slug(section), []))


def all_resources() -> List[Resource]:
    out: List[Resource] = []
    for v in load().values():
        out.extend(v)
    return out


def search(query: str, limit: int = 25) -> List[Resource]:
    """Naive substring search across title + section."""
    q = query.lower().strip()
    if not q:
        return []
    out: List[Resource] = []
    for r in all_resources():
        if q in r.title.lower() or q in r.section.lower():
            out.append(r)
            if len(out) >= limit:
                break
    return out


# Loose mapping from common Rhodawk vulnerability tags to the README
# sections they're most relevant to.  Used by knowledge_rag.py to seed
# the embedding store and by red_team_fuzzer.py to attach reading
# material to a generated PoC.
TAG_TO_SECTIONS: Dict[str, List[str]] = {
    "xss":                ["js_analysis", "writeups", "challenges", "blogs"],
    "dom_xss":            ["writeups", "blogs", "challenges"],
    "postmessage":        ["writeups", "blogs"],
    "csp":                ["csp_resources"],
    "csp_bypass":         ["csp_resources"],
    "prototype_pollution": ["prototype_pollution"],
    "cors":               ["internals", "blogs"],
    "iframe":             ["internals"],
    "client_side":        ["js_analysis", "blogs", "writeups"],
    "websocket":          ["blogs", "important_concepts_to_know"],
}


def for_tag(tag: str, limit: int = 10) -> List[Resource]:
    sections = TAG_TO_SECTIONS.get(_slug(tag), [])
    out: List[Resource] = []
    seen = set()
    for sec in sections:
        for r in get_section(sec):
            if r.url in seen:
                continue
            seen.add(r.url)
            out.append(r)
            if len(out) >= limit:
                return out
    return out


def stats() -> Dict[str, object]:
    s = load()
    return {
        "resources_path": str(RESOURCES_PATH),
        "available": bool(s),
        "sections": len(s),
        "total_resources": sum(len(v) for v in s.values()),
        "section_list": sorted(s.keys()),
    }


def seed_urls(limit: int = 50) -> List[str]:
    """Flat list of unique URLs — handy as input to knowledge_rag.py's
    ingestion loop (``ingest_url(...)``)."""
    seen: List[str] = []
    s = set()
    for r in all_resources():
        if r.url in s:
            continue
        s.add(r.url)
        seen.append(r.url)
        if len(seen) >= limit:
            break
    return seen


__all__ = [
    "Resource",
    "load",
    "list_sections",
    "get_section",
    "all_resources",
    "search",
    "for_tag",
    "seed_urls",
    "stats",
    "TAG_TO_SECTIONS",
]
