"""
Rhodawk AI — Semantic Logic Extractor (Ethical Research Mode)
=============================================================
STATIC ANALYSIS ONLY — no code is executed by this module.

Maps the application's trust state machine across files to identify
"Assumption Gaps" — points where developer intent diverges from actual
code behaviour. All output is JSON for human review.

Orchestrated by Nous Hermes 3 via OpenRouter.
"""

from __future__ import annotations

import glob
import json
import os
import re
import time
from pathlib import Path
from typing import Optional

import requests

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
HERMES_MODEL = os.getenv(
    "RHODAWK_RESEARCH_MODEL",
    "nousresearch/hermes-3-llama-3.1-405b:free",
)

_PRIORITY_KEYWORDS = [
    "auth", "token", "session", "permission", "privilege", "trust",
    "validate", "sanitize", "parse", "decode", "deserialize", "marshal",
    "memory", "alloc", "buffer", "exec", "eval", "inject", "sign", "verify",
    "secret", "password", "credential", "acl", "role", "scope", "grant",
]

_SKIP_DIRS = {".git", "vendor", "node_modules", "__pycache__", ".tox", "dist", "build"}


def _hermes(system: str, user: str, max_tokens: int = 4096) -> str:
    """Call Nous Hermes 3 via OpenRouter."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://rhodawk.ai",
        "X-Title": "Rhodawk Ethical Security Research",
    }
    payload = {
        "model": HERMES_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers, json=payload, timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _find_relevant_files(repo_dir: str, language: str) -> list[str]:
    lang_patterns: dict[str, list[str]] = {
        "python":     ["**/*.py"],
        "javascript": ["**/*.js", "**/*.mjs"],
        "typescript": ["**/*.ts"],
        "go":         ["**/*.go"],
        "java":       ["**/*.java"],
        "rust":       ["**/*.rs"],
        "c":          ["**/*.c", "**/*.h"],
        "cpp":        ["**/*.cpp", "**/*.hpp", "**/*.h"],
        "ruby":       ["**/*.rb"],
    }
    patterns = lang_patterns.get(language.lower(), ["**/*.py"])

    all_files: list[str] = []
    for pat in patterns:
        for path in glob.glob(os.path.join(repo_dir, pat), recursive=True):
            rel = os.path.relpath(path, repo_dir)
            if any(s in rel for s in _SKIP_DIRS):
                continue
            all_files.append(rel)

    priority = [f for f in all_files if any(kw in f.lower() for kw in _PRIORITY_KEYWORDS)]
    rest = [f for f in all_files if f not in priority]
    return (priority + rest)[:30]


def _read_file_head(repo_dir: str, rel_path: str, max_lines: int = 200) -> str:
    try:
        text = Path(os.path.join(repo_dir, rel_path)).read_text(
            encoding="utf-8", errors="replace"
        )
        return "\n".join(text.splitlines()[:max_lines])
    except Exception:
        return ""


def _extract_json(text: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def extract_trust_boundaries(repo_dir: str, file_paths: list[str]) -> dict:
    """
    Static analysis pass: asks Hermes to map trust states and find assumption gaps.
    Returns a JSON-serialisable state machine graph.
    """
    snippets = []
    for rel in file_paths[:20]:
        head = _read_file_head(repo_dir, rel)
        if head:
            snippets.append(f"=== {rel} ===\n{head}")

    combined = "\n\n".join(snippets)[:14000]

    system = (
        "You are a senior security researcher conducting responsible vulnerability research. "
        "You perform STATIC analysis only — you never execute code. "
        "Your goal is to map trust state machines and identify assumption gaps where developer "
        "intent diverges from actual code behaviour. "
        "Output valid JSON only — no prose outside the JSON block."
    )

    user = f"""Analyse the source code below and output a trust state machine graph.

Identify:
1. Where data enters the system (UNTRUSTED)
2. Validation / sanitisation steps (TRANSITION)
3. Where data is treated as trusted (TRUSTED)
4. ASSUMPTION GAPS — points where the code assumes safety without sufficient proof

Return ONLY this JSON structure:
{{
  "language": "detected language",
  "trust_states": [
    {{"id": "s1", "name": "...", "type": "UNTRUSTED|TRANSITION|TRUSTED",
      "files": ["file.py"], "description": "..."}}
  ],
  "transitions": [
    {{"from": "s1", "to": "s2", "condition": "...", "file": "file.py", "line_hint": "..."}}
  ],
  "assumption_gaps": [
    {{
      "id": "gap_001",
      "severity_hypothesis": "P1|P2|P3",
      "file": "relative/path.py",
      "line_hint": "function name or ~line number",
      "description": "What the developer assumed vs what can actually reach this point",
      "untrusted_input": "What untrusted data reaches here",
      "bypassed_check": "What validation is missing or insufficient",
      "potential_impact": "Theoretical worst-case consequence",
      "confidence": "HIGH|MEDIUM|LOW",
      "requires_human_verification": true
    }}
  ]
}}

SOURCE CODE:
{combined}"""

    try:
        raw = _hermes(system, user)
        result = _extract_json(raw)
        if result:
            return result
    except Exception as e:
        return {"error": str(e), "assumption_gaps": []}

    return {"assumption_gaps": []}


def run_semantic_extraction(repo_dir: str, language: str = "python") -> dict:
    """
    Main entry point for the semantic analysis pipeline.
    Pure static analysis — no code is executed.

    Returns a dict containing:
      - trust_states
      - transitions
      - assumption_gaps  (each tagged requires_human_verification=True)
      - analyzed_files
      - status: always "PENDING_HUMAN_REVIEW"
    """
    relevant_files = _find_relevant_files(repo_dir, language)
    if not relevant_files:
        return {
            "error": "No source files found for the detected language.",
            "assumption_gaps": [],
            "status": "PENDING_HUMAN_REVIEW",
        }

    result = extract_trust_boundaries(repo_dir, relevant_files)
    result["analyzed_files"] = relevant_files
    result["repo_dir"] = repo_dir
    result["language"] = language
    result["extracted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    result["status"] = "PENDING_HUMAN_REVIEW"

    for gap in result.get("assumption_gaps", []):
        gap["requires_human_verification"] = True

    return result
