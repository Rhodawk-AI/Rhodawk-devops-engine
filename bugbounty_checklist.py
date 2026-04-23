"""
bugbounty_checklist.py
──────────────────────
In-process loader for the vendored Galaxy-Bugbounty-Checklist
(https://github.com/0xmaximus/Galaxy-Bugbounty-Checklist).

The repo is a hand-curated bug bounty methodology library — one folder per
vulnerability class (XSS, SSRF, SQLi, OAuth, IDOR, CSRF bypass, …),
each containing a long-form checklist plus, where applicable, a payload
file (e.g. ``sql_injection/SQL.txt``, ``xss_payloads/README.md``).

This module loads it from ``vendor/galaxy_bugbounty/`` at import time so
that the rest of the system can:

  * Look up a checklist by category or by CWE / vulnerability tag
    (``vuln_classifier.py``, ``red_team_fuzzer.py``).
  * Pull payload corpora for a category (used by the fuzzer + harness
    factory to seed boundary-value inputs).
  * Surface "what should I check next" hints to the orchestrator while
    triaging a candidate finding.
  * Expose the same data through a tiny REST adapter so other engines
    (and the OpenClaude tool layer) can consume it without re-parsing
    markdown on every call.

Design rules
────────────
1. Pure Python stdlib — no heavy dependencies, no I/O at import time
   beyond a single directory scan.
2. Zero hard dependency: if the vendor directory is missing the module
   degrades to empty-result helpers and logs a warning instead of
   raising, so the orchestrator keeps working.
3. Read-only — never mutate the vendored content.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional

log = logging.getLogger("rhodawk.bugbounty")

# ─── Locations ─────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
VENDOR_DIR = Path(
    os.environ.get("RHODAWK_GALAXY_DIR", str(_HERE / "vendor" / "galaxy_bugbounty"))
)

# CWE / common-tag → vendored category-folder slug.
# Keep the keys lowercase, snake_case-friendly so callers can match
# either CWE numbers or a normalized vulnerability label.
CWE_CATEGORY_MAP: Dict[str, str] = {
    # XSS family
    "cwe-79": "xss_payloads",
    "xss": "xss_payloads",
    "reflected_xss": "xss_payloads",
    "stored_xss": "xss_payloads",
    "dom_xss": "xss_payloads",
    # Injection
    "cwe-89": "sql_injection",
    "sqli": "sql_injection",
    "sql_injection": "sql_injection",
    "cwe-93": "crlf_injection",
    "crlf": "crlf_injection",
    # SSRF
    "cwe-918": "ssrf",
    "ssrf": "ssrf",
    # CSRF
    "cwe-352": "csrf_bypass",
    "csrf": "csrf_bypass",
    # Access control / IDOR
    "cwe-284": "broken_access_control",
    "cwe-285": "broken_access_control",
    "cwe-639": "broken_access_control",
    "idor": "broken_access_control",
    "bac": "broken_access_control",
    # Auth / account takeover / 2FA
    "cwe-287": "account_takeover",
    "ato": "account_takeover",
    "account_takeover": "account_takeover",
    "2fa_bypass": "2fa_bypass",
    # Open redirect
    "cwe-601": "open_redirect",
    "open_redirect": "open_redirect",
    # Sensitive data / info disclosure
    "cwe-200": "sensitive_data_exposure",
    "info_disclosure": "sensitive_data_exposure",
    # File upload
    "cwe-434": "file_upload",
    "file_upload": "file_upload",
    # Rate limit
    "rate_limit": "rate_limit_bypass",
    "rate_limit_bypass": "rate_limit_bypass",
    # OAuth
    "oauth": "oauth",
    # Smuggling
    "cwe-444": "http_request_smuggling",
    "request_smuggling": "http_request_smuggling",
    # Cache deception
    "cache_deception": "web_cache_deception",
    "web_cache_deception": "web_cache_deception",
    # WordPress / IIS / Log4j
    "wordpress": "wordpress",
    "iis": "internet_information_services_iis",
    "log4j": "log4shell",
    "log4shell": "log4shell",
    # Reset password
    "reset_password": "reset_password_vulnerabilities",
    # Param pollution
    "hpp": "parameter_pollution",
    "parameter_pollution": "parameter_pollution",
    # OSINT recon
    "osint": "osint",
    # API
    "api": "api_security",
    "api_security": "api_security",
    # DoS
    "cwe-400": "dos",
    "dos": "dos",
}


# ─── Data model ────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Checklist:
    """A single vulnerability-class checklist as vendored from Galaxy."""
    category: str                     # snake_case slug, e.g. "ssrf"
    title: str                        # human-readable title
    markdown: str                     # full README content
    payloads: List[str] = field(default_factory=list)  # raw payload strings
    payload_files: List[str] = field(default_factory=list)
    source_dir: str = ""

    def summary(self, max_chars: int = 600) -> str:
        body = re.sub(r"\s+", " ", self.markdown).strip()
        return body[:max_chars] + ("…" if len(body) > max_chars else "")

    def to_dict(self) -> Dict[str, object]:
        return {
            "category": self.category,
            "title": self.title,
            "summary": self.summary(),
            "payload_count": len(self.payloads),
            "payload_files": list(self.payload_files),
            "source_dir": self.source_dir,
        }


# ─── Loader ────────────────────────────────────────────────────────────
def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        log.warning("could not read %s: %s", path, exc)
        return ""


def _extract_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback.replace("_", " ").title()


def _split_payloads(text: str) -> List[str]:
    """Split a payload file into individual non-empty payload lines.

    Galaxy payload files are mostly newline-separated; some entries
    contain inline whitespace which we preserve.
    """
    lines = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


@lru_cache(maxsize=1)
def load_all() -> Dict[str, Checklist]:
    """Return ``{category_slug: Checklist}`` for every vendored category."""
    out: Dict[str, Checklist] = {}
    if not VENDOR_DIR.is_dir():
        log.warning("Galaxy bug bounty vendor dir missing at %s", VENDOR_DIR)
        return out

    for entry in sorted(VENDOR_DIR.iterdir()):
        if not entry.is_dir():
            continue
        readme = next(
            (p for p in entry.iterdir() if p.name.lower() == "readme.md"),
            None,
        )
        markdown = _read(readme) if readme else ""
        title = _extract_title(markdown, entry.name)

        payloads: List[str] = []
        payload_files: List[str] = []
        for f in sorted(entry.iterdir()):
            if f.is_file() and f.suffix.lower() == ".txt":
                payload_files.append(f.name)
                payloads.extend(_split_payloads(_read(f)))

        out[entry.name] = Checklist(
            category=entry.name,
            title=title,
            markdown=markdown,
            payloads=payloads,
            payload_files=payload_files,
            source_dir=str(entry),
        )
    return out


# ─── Public API ────────────────────────────────────────────────────────
def list_categories() -> List[str]:
    return sorted(load_all().keys())


def get_checklist(category: str) -> Optional[Checklist]:
    """Look up by exact category slug (e.g. ``"ssrf"``)."""
    return load_all().get(category)


def _normalize_tag(tag: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", tag.lower()).strip("_")


def match_for_tag(tag: str) -> Optional[Checklist]:
    """Map an arbitrary tag (CWE id, vuln label, classifier output, …)
    to a checklist.  Returns ``None`` if no mapping is known.
    """
    if not tag:
        return None
    norm = _normalize_tag(tag)
    cats = load_all()

    # 1. exact category
    if norm in cats:
        return cats[norm]
    # 2. mapped CWE / synonym
    slug = CWE_CATEGORY_MAP.get(norm)
    if slug and slug in cats:
        return cats[slug]
    # 3. CWE prefix variants ("cwe79" / "79")
    if norm.isdigit():
        slug = CWE_CATEGORY_MAP.get(f"cwe-{norm}")
        if slug and slug in cats:
            return cats[slug]
    # 4. fuzzy contains
    for key, cl in cats.items():
        if norm in key or key in norm:
            return cl
    return None


def payloads_for(tag_or_category: str, limit: int = 200) -> List[str]:
    """Return up to ``limit`` payload strings for a category/tag.

    Used by ``red_team_fuzzer.py`` and ``harness_factory.py`` to seed
    boundary-value test corpora — Galaxy's ``SQL.txt`` is a classic
    SQLi corpus, ``xss_payloads/README.md`` carries a long XSS list
    embedded in a markdown table.
    """
    cl = match_for_tag(tag_or_category)
    if not cl:
        return []
    payloads = list(cl.payloads)
    # If no .txt files, scrape inline ``code`` snippets from the README
    # which is where many of the XSS / SSRF payloads actually live.
    if not payloads:
        payloads = re.findall(r"`([^`\n]{2,200})`", cl.markdown)
    # De-duplicate while preserving order.
    seen, dedup = set(), []
    for p in payloads:
        if p in seen:
            continue
        seen.add(p)
        dedup.append(p)
        if len(dedup) >= limit:
            break
    return dedup


def hints_for_finding(
    *,
    cwe: str = "",
    label: str = "",
    description: str = "",
    max_bullets: int = 8,
) -> List[str]:
    """Return short bullet-point reminders extracted from the matching
    checklist — meant to be injected into the orchestrator's triage
    prompt so the model considers Galaxy's hand-written tradecraft when
    assessing a finding."""
    cl = match_for_tag(cwe) or match_for_tag(label)
    if not cl and description:
        # last-ditch keyword scan
        d_norm = description.lower()
        for key in CWE_CATEGORY_MAP:
            if key in d_norm:
                cl = match_for_tag(key)
                if cl:
                    break
    if not cl:
        return []

    bullets = re.findall(
        r"^\s*[-*]\s+(.+)$",
        cl.markdown,
        flags=re.MULTILINE,
    )
    out, seen = [], set()
    for b in bullets:
        s = b.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= max_bullets:
            break
    return out


def stats() -> Dict[str, object]:
    cats = load_all()
    return {
        "vendor_dir": str(VENDOR_DIR),
        "available": bool(cats),
        "categories": len(cats),
        "total_payloads": sum(len(c.payloads) for c in cats.values()),
        "category_list": sorted(cats.keys()),
    }


__all__ = [
    "Checklist",
    "CWE_CATEGORY_MAP",
    "load_all",
    "list_categories",
    "get_checklist",
    "match_for_tag",
    "payloads_for",
    "hints_for_finding",
    "stats",
]
