"""
ARCHITECT — semantic skill selector (Masterplan §5).

Upgrades the keyword-based ``architect/skill_registry`` with **semantic
similarity ranking** so the right domain skills are loaded into the LLM
context regardless of how the task is phrased.

Tier-5 design (Masterplan §7):
    * Embeddings:  sentence-transformers / MiniLM-L6-v2  (CPU, $0)
    * Fallback:    deterministic keyword-overlap scorer  (no model needed)
    * Cache:       skill embeddings hashed on disk (JSON) so the model loads
                   *once* per process and *never* recomputes between calls.

Public surface:

    select_for_task(task_description, repo_languages, repo_tech_stack,
                    attack_phase, top_k=5) -> str
        Returns a single XML-flavoured ``<skills>...</skills>`` block ready
        to be prepended to any system prompt.

    pack(task_description, ...) -> list[Skill]
        Same logic but returns the matched Skill objects (for callers who
        want to render their own context format).

The module is designed to **never raise** in production: every external
dependency (sentence-transformers, numpy, sklearn) is optional and falls
back to a pure-Python implementation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from . import skill_registry

LOG = logging.getLogger("architect.skill_selector")

CACHE_DIR = Path(os.getenv("ARCHITECT_SKILL_CACHE", "/tmp/architect_skill_cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Phase → list of skill-name substrings that should get a relevance boost.
PHASE_BOOSTS: dict[str, tuple[str, ...]] = {
    "recon":   ("recon", "subdomain", "wayback", "shodan", "httpx", "fingerprint"),
    "static":  ("static", "sast", "taint", "semgrep", "ast", "code", "memory"),
    "dynamic": ("fuzz", "dynamic", "browser", "runtime", "frida"),
    "exploit": ("exploit", "rop", "heap", "buffer", "pwn", "shellcode", "primitive"),
    "report":  ("report", "p1", "p2", "cvss", "submission", "platform"),
    "triage":  ("methodology", "reference", "index", "report"),
}

_LOCK = threading.Lock()
_MODEL: Any = None
_EMBEDS: dict[str, list[float]] = {}
_SKILLS: list[skill_registry.Skill] = []


# ── lazy model loading ──────────────────────────────────────────────────────
def _try_load_model() -> Any:
    """Best-effort load of MiniLM. Returns None on any failure."""
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        model_name = os.getenv("ARCHITECT_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        LOG.info("skill_selector: loading embed model %s", model_name)
        _MODEL = SentenceTransformer(model_name)
        return _MODEL
    except Exception as exc:  # noqa: BLE001
        LOG.warning("skill_selector: sentence-transformers unavailable (%s) — using keyword fallback", exc)
        _MODEL = False  # sentinel: don't try again
        return None


# ── embedding cache ─────────────────────────────────────────────────────────
def _skill_hash(skill: skill_registry.Skill) -> str:
    h = hashlib.sha256()
    h.update(skill.name.encode())
    h.update(skill.body.encode())
    return h.hexdigest()[:16]


def _cache_path_for(model_name: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", model_name)
    return CACHE_DIR / f"skills_{safe}.json"


def _load_disk_cache(model_name: str) -> dict[str, list[float]]:
    p = _cache_path_for(model_name)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception as exc:  # noqa: BLE001
        LOG.debug("skill_selector cache read failed: %s", exc)
        return {}


def _save_disk_cache(model_name: str, data: dict[str, list[float]]) -> None:
    p = _cache_path_for(model_name)
    try:
        p.write_text(json.dumps(data))
    except Exception as exc:  # noqa: BLE001
        LOG.debug("skill_selector cache write failed: %s", exc)


def _ensure_skill_embeddings() -> dict[str, list[float]]:
    """
    Return ``{skill_name: vector}`` for the entire registry. Computes only
    the vectors that aren't already cached. If no embedding model is
    available, returns an empty dict (callers must fall back to keywords).
    """
    global _EMBEDS, _SKILLS
    with _LOCK:
        if not _SKILLS:
            _SKILLS = skill_registry.load_all()
        model = _try_load_model()
        if not model:
            return {}
        model_name = os.getenv("ARCHITECT_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        cache = _load_disk_cache(model_name)
        missing: list[skill_registry.Skill] = []
        result: dict[str, list[float]] = {}
        for s in _SKILLS:
            key = f"{s.name}:{_skill_hash(s)}"
            if key in cache:
                result[s.name] = cache[key]
            else:
                missing.append(s)
        if missing:
            try:
                texts = [f"{m.name}\n{m.domain}\n{m.body[:2000]}" for m in missing]
                vecs = model.encode(texts, normalize_embeddings=True).tolist()
                for s, v in zip(missing, vecs):
                    key = f"{s.name}:{_skill_hash(s)}"
                    cache[key] = v
                    result[s.name] = v
                _save_disk_cache(model_name, cache)
            except Exception as exc:  # noqa: BLE001
                LOG.warning("skill_selector: embedding failed (%s) — keyword fallback", exc)
                return {}
        _EMBEDS = result
        return result


# ── similarity helpers ──────────────────────────────────────────────────────
def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _keyword_score(skill: skill_registry.Skill, tokens: set[str]) -> float:
    """Pure-Python fallback ranker. Counts shared whitespace tokens."""
    body_tokens = set(re.findall(r"[a-z0-9_-]{3,}", (skill.name + " " + skill.body).lower()))
    if not body_tokens:
        return 0.0
    overlap = body_tokens & tokens
    return len(overlap) / max(1, math.sqrt(len(body_tokens)))


def _phase_boost(skill: skill_registry.Skill, phase: str) -> float:
    needles = PHASE_BOOSTS.get(phase.lower(), ())
    if not needles:
        return 0.0
    name = (skill.name + " " + skill.domain + " " + skill.path.as_posix()).lower()
    return 0.10 * sum(1 for n in needles if n in name)


# ── public API ──────────────────────────────────────────────────────────────
@dataclass
class Match:
    skill: skill_registry.Skill
    score: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.skill.name,
            "domain": self.skill.domain,
            "path": str(self.skill.path),
            "score": round(self.score, 4),
            "reason": self.reason,
        }


def pack(
    task_description: str,
    *,
    repo_languages: Iterable[str] | None = None,
    repo_tech_stack: Iterable[str] | None = None,
    attack_phase: str = "static",
    top_k: int = 5,
    pin: Iterable[str] | None = None,
) -> list[Match]:
    """
    Return up to ``top_k`` matched skills (highest score first).

    ``pin`` — names of skills that must always be included regardless of
    score (useful for "always carry the bug-bounty methodology playbook").
    """
    if not _SKILLS:
        _ensure_skill_embeddings()  # also populates _SKILLS even on fallback
    if not _SKILLS:
        return []

    langs = [s.lower() for s in (repo_languages or [])]
    techs = [s.lower() for s in (repo_tech_stack or [])]
    query = " ".join([task_description, attack_phase, *langs, *techs])

    embeds = _ensure_skill_embeddings()
    use_embed = bool(embeds)
    matches: list[Match] = []

    if use_embed:
        try:
            qv = _MODEL.encode([query], normalize_embeddings=True).tolist()[0]
        except Exception as exc:  # noqa: BLE001
            LOG.warning("skill_selector: query encode failed (%s) — keyword fallback", exc)
            use_embed = False

    if use_embed:
        for s in _SKILLS:
            v = embeds.get(s.name)
            if not v:
                continue
            score = _cosine(qv, v) + _phase_boost(s, attack_phase)
            matches.append(Match(skill=s, score=score, reason="semantic"))
    else:
        tokens = set(re.findall(r"[a-z0-9_-]{3,}", query.lower()))
        for s in _SKILLS:
            score = _keyword_score(s, tokens) + _phase_boost(s, attack_phase)
            matches.append(Match(skill=s, score=score, reason="keyword"))

    # Boost via the registry's structured trigger profile too.
    profile = {"languages": langs, "asset_types": techs, "frameworks": techs}
    for m in matches:
        m.score += 0.05 * m.skill.matches(profile)

    matches.sort(key=lambda m: m.score, reverse=True)
    chosen = matches[:top_k]
    pinned = {p.lower() for p in (pin or [])}
    if pinned:
        already = {m.skill.name.lower() for m in chosen}
        for s in _SKILLS:
            if s.name.lower() in pinned and s.name.lower() not in already:
                chosen.append(Match(skill=s, score=999.0, reason="pinned"))
    return chosen


def select_for_task(
    task_description: str,
    repo_languages: Iterable[str] | None = None,
    repo_tech_stack: Iterable[str] | None = None,
    attack_phase: str = "static",
    top_k: int = 5,
    pin: Iterable[str] | None = None,
) -> str:
    """
    Render the matched skills into a context block ready to be prepended to
    any LLM system prompt. Returns ``""`` when no skills match.
    """
    chosen = pack(
        task_description,
        repo_languages=repo_languages,
        repo_tech_stack=repo_tech_stack,
        attack_phase=attack_phase,
        top_k=top_k,
        pin=pin,
    )
    if not chosen:
        return ""

    parts: list[str] = ["<skills>"]
    parts.append(
        f"  <!-- Loaded {len(chosen)} skill(s) for phase={attack_phase!r}. "
        "Apply them precisely; cite the skill name when you use it. -->"
    )
    for m in chosen:
        parts.append(f"  <skill name=\"{m.skill.name}\" domain=\"{m.skill.domain}\" "
                     f"score=\"{m.score:.3f}\" reason=\"{m.reason}\">")
        parts.append(m.skill.body.strip())
        parts.append("  </skill>")
    parts.append("</skills>")
    return "\n".join(parts)


def explain(task_description: str, **kwargs: Any) -> dict[str, Any]:
    """Diagnostic: returns the ranked match list as JSON-able dicts."""
    chosen = pack(task_description, **kwargs)
    return {
        "task": task_description,
        "engine": "semantic" if _try_load_model() else "keyword",
        "matches": [m.to_dict() for m in chosen],
    }


def stats() -> dict[str, Any]:
    skills = skill_registry.load_all()
    embeds = _EMBEDS or {}
    return {
        "total_skills": len(skills),
        "embedded_skills": len(embeds),
        "engine": "semantic" if _try_load_model() else "keyword",
        "cache_dir": str(CACHE_DIR),
    }
