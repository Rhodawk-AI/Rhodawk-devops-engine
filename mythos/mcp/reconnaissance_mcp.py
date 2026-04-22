"""
reconnaissance-mcp — Mythos recon MCP server (§4.6 of MYTHOS_PLAN.md).

Exposes language / framework / dependency / attack-surface fingerprinting as
MCP tools so the Planner agent can call them via the standard tool bus
instead of importing the helpers directly.

Tools
-----

* ``fingerprint_repo``       — language + framework + build-system summary
* ``enumerate_dependencies`` — manifest parsers (pyproject, package.json, go.mod, Cargo.toml)
* ``map_attack_surface``     — heuristic surface (HTTP routes, CLI entry-points, deserialisers)

The server boots cleanly even when no recon target is on disk; every tool
returns ``{"available": False, "reason": "..."}`` instead of raising.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from ._mcp_runtime import MCPServer

server = MCPServer(name="reconnaissance-mcp")

_LANG_HINTS = {
    "python":     [".py", "pyproject.toml", "requirements.txt", "setup.py", "Pipfile"],
    "javascript": [".js", ".mjs", ".cjs", "package.json", "yarn.lock"],
    "typescript": [".ts", ".tsx", "tsconfig.json"],
    "go":         [".go", "go.mod", "go.sum"],
    "rust":       [".rs", "Cargo.toml", "Cargo.lock"],
    "java":       [".java", "pom.xml", "build.gradle", "build.gradle.kts"],
    "kotlin":     [".kt", ".kts"],
    "c":          [".c", ".h"],
    "cpp":        [".cc", ".cpp", ".cxx", ".hpp"],
    "ruby":       [".rb", "Gemfile"],
    "php":        [".php", "composer.json"],
    "csharp":     [".cs", ".csproj", ".sln"],
    "swift":      [".swift", "Package.swift"],
}

_FRAMEWORK_HINTS = {
    "django":   ["manage.py", "settings.py"],
    "flask":    ["from flask import", "Flask("],
    "fastapi":  ["from fastapi import", "FastAPI("],
    "express":  ["require('express')", 'from "express"'],
    "rails":    ["config/routes.rb"],
    "spring":   ["@SpringBootApplication"],
    "actix":    ["actix_web::"],
    "gin":      ["gin.New(", "gin.Default("],
}


def _scan(root: Path) -> dict[str, Any]:
    files: list[Path] = []
    for dp, _, fns in os.walk(root):
        # Skip the usual heavy/derived directories.
        if any(seg in dp for seg in (".git", "node_modules", ".venv", "__pycache__",
                                     "dist", "build", "target")):
            continue
        for fn in fns:
            files.append(Path(dp) / fn)
            if len(files) >= 5000:
                return {"files": files, "truncated": True}
    return {"files": files, "truncated": False}


@server.tool("fingerprint_repo", schema={"path": "string"})
def fingerprint_repo(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"available": False, "reason": f"path does not exist: {path}"}
    scan = _scan(p)
    files = scan["files"]
    langs: dict[str, int] = {}
    for f in files:
        for lang, hints in _LANG_HINTS.items():
            if any(str(f).endswith(h) or f.name == h for h in hints):
                langs[lang] = langs.get(lang, 0) + 1
                break
    frameworks: list[str] = []
    text_blob = ""
    for f in files[:300]:
        try:
            if f.suffix in {".py", ".js", ".ts", ".rb", ".go", ".java", ".kt"}:
                text_blob += f.read_text(errors="ignore")[:8000] + "\n"
        except Exception:
            continue
    for fw, hints in _FRAMEWORK_HINTS.items():
        if any(h in text_blob or (Path(path) / h).exists() for h in hints):
            frameworks.append(fw)
    return {
        "available": True,
        "languages": sorted(langs, key=lambda k: -langs[k]),
        "language_file_counts": langs,
        "frameworks": sorted(set(frameworks)),
        "file_count": len(files),
        "truncated": scan["truncated"],
    }


@server.tool("enumerate_dependencies", schema={"path": "string"})
def enumerate_dependencies(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"available": False, "reason": f"path does not exist: {path}"}
    deps: dict[str, list[str]] = {}

    # Python — pyproject / requirements
    for pf in p.rglob("requirements*.txt"):
        try:
            deps.setdefault("python", []).extend(
                ln.split("==")[0].split(">=")[0].split("[")[0].strip()
                for ln in pf.read_text(errors="ignore").splitlines()
                if ln.strip() and not ln.startswith("#"))
        except Exception:
            continue
    pyproj = p / "pyproject.toml"
    if pyproj.exists():
        try:
            blob = pyproj.read_text(errors="ignore")
            deps.setdefault("python", []).extend(re.findall(r'"([a-zA-Z0-9_\-]+)\s*[><=]', blob))
        except Exception:
            pass

    # Node
    for pkg in p.rglob("package.json"):
        try:
            j = json.loads(pkg.read_text(errors="ignore"))
            deps.setdefault("node", []).extend(list((j.get("dependencies") or {}).keys()))
            deps.setdefault("node-dev", []).extend(list((j.get("devDependencies") or {}).keys()))
        except Exception:
            continue

    # Go
    gomod = p / "go.mod"
    if gomod.exists():
        try:
            deps["go"] = re.findall(r"^\s*([\w.\-/]+)\s+v[\d.]+", gomod.read_text(), re.M)
        except Exception:
            pass

    # Rust
    cargo = p / "Cargo.toml"
    if cargo.exists():
        try:
            deps["rust"] = re.findall(r"^([a-zA-Z0-9_\-]+)\s*=", cargo.read_text(), re.M)
        except Exception:
            pass

    # de-dupe
    return {"available": True, "dependencies": {k: sorted(set(v)) for k, v in deps.items() if v}}


@server.tool("map_attack_surface", schema={"path": "string"})
def map_attack_surface(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"available": False, "reason": f"path does not exist: {path}"}
    surface = {"http_routes": [], "cli_entrypoints": [], "deserialisers": [], "subprocess_calls": []}
    patterns = {
        "http_routes": re.compile(
            r"@(?:app|router|api)\.(?:get|post|put|delete|patch)\(\s*['\"]([^'\"]+)"),
        "cli_entrypoints": re.compile(r"argparse\.ArgumentParser|click\.command|@app\.command"),
        "deserialisers": re.compile(r"\b(pickle\.loads|yaml\.load|marshal\.loads|"
                                    r"eval\(|exec\(|JSON\.parse\()"),
        "subprocess_calls": re.compile(
            r"subprocess\.(?:run|Popen|call|check_output)|os\.system|child_process\."),
    }
    for f in p.rglob("*.py"):
        try:
            blob = f.read_text(errors="ignore")
        except Exception:
            continue
        for key, rx in patterns.items():
            for m in rx.finditer(blob):
                hit = m.group(1) if m.groups() else m.group(0)
                surface[key].append({"file": str(f.relative_to(p)), "match": hit[:120]})
                if len(surface[key]) > 200:
                    break
    surface["totals"] = {k: len(v) for k, v in surface.items() if isinstance(v, list)}
    return {"available": True, **surface}


def main() -> None:  # pragma: no cover
    server.serve_stdio()


if __name__ == "__main__":  # pragma: no cover
    main()
