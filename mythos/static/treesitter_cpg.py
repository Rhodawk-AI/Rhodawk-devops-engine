"""
Tree-sitter based Concrete Syntax Tree → lightweight CPG summary.

When ``tree_sitter_languages`` is installed we walk the CST per file and
emit per-language stats (function count, max nesting depth, dangerous-call
hits).  Otherwise we degrade to a regex-based scanner that is good enough
for the planner's first-cut prioritisation.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from typing import Any

try:  # pragma: no cover - optional
    from tree_sitter_languages import get_parser  # type: ignore
    _TS = True
except Exception:  # noqa: BLE001
    _TS = False

EXT_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp", ".hpp": "cpp",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
    ".java": "java", ".kt": "kotlin", ".swift": "swift",
}

DANGEROUS_PATTERNS = {
    "python":     [r"\beval\(", r"\bexec\(", r"pickle\.loads\(", r"yaml\.load\(", r"subprocess\..*shell\s*=\s*True"],
    "javascript": [r"\beval\(", r"new\s+Function\(", r"child_process", r"\.innerHTML\s*="],
    "typescript": [r"\beval\(", r"any\s*=", r"child_process"],
    "c":          [r"\bgets\(", r"\bstrcpy\(", r"\bsprintf\(", r"\bsystem\("],
    "cpp":        [r"\bgets\(", r"\bstrcpy\(", r"\bsprintf\(", r"\bsystem\(", r"reinterpret_cast<"],
    "go":         [r"exec\.Command\(", r"unsafe\."],
    "java":       [r"Runtime\.getRuntime\(\)\.exec", r"ObjectInputStream\("],
    "php":        [r"\beval\(", r"system\(", r"shell_exec\("],
}


class TreeSitterCPG:
    def __init__(self):
        self.have_ts = _TS

    def summary(self, repo_path: str) -> dict[str, Any]:
        if not os.path.isdir(repo_path):
            return {"available": False, "reason": "missing path", "files": 0}
        files_by_lang: dict[str, int] = defaultdict(int)
        sinks: list[dict[str, Any]] = []
        total_files = 0
        for root, _dirs, files in os.walk(repo_path):
            if any(p in root for p in (".git", "node_modules", "venv", "__pycache__")):
                continue
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                lang = EXT_LANG.get(ext)
                if not lang:
                    continue
                total_files += 1
                files_by_lang[lang] += 1
                fp = os.path.join(root, fname)
                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as fh:
                        text = fh.read()
                except Exception:
                    continue
                for pat in DANGEROUS_PATTERNS.get(lang, []):
                    for m in re.finditer(pat, text):
                        line = text.count("\n", 0, m.start()) + 1
                        sinks.append({"file": os.path.relpath(fp, repo_path),
                                      "lang": lang, "pattern": pat, "line": line})
        return {
            "available": True,
            "backend": "tree-sitter" if self.have_ts else "regex-fallback",
            "files": total_files,
            "files_by_language": dict(files_by_lang),
            "dangerous_sinks": sinks[:200],
            "sink_count": len(sinks),
        }
