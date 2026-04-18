"""
Rhodawk AI — Taint Analysis Engine
=====================================
Tracks untrusted input as it flows through source code to dangerous sinks.
Language-agnostic: Python (AST), JS/TS (regex+AST heuristics), Go (grep patterns).

Also exposes map_attack_surface() used by Hermes recon phase.
"""

from __future__ import annotations

import ast
import glob
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TaintFlow:
    source: str          # where untrusted input enters
    sink: str            # dangerous function it reaches
    path: list[str]      # chain of variable names/calls
    file_path: str
    source_line: int
    sink_line: int
    cwe_candidates: list[str]
    confidence: float


@dataclass
class AttackSurface:
    entry_points: list[dict]        # functions reachable from network/user
    dangerous_sinks: list[dict]     # calls to exec/eval/open/format etc
    security_critical_files: list[str]
    external_dependencies: list[str]
    crypto_operations: list[dict]
    authentication_flows: list[dict]
    deserialization_points: list[dict]
    language: str


_PYTHON_SOURCES = {
    "input", "sys.argv", "os.environ.get", "os.getenv",
    "request.args.get", "request.form.get", "request.json",
    "request.data", "request.body", "request.POST", "request.GET",
    "socket.recv", "socket.recvfrom", "read", "readline",
    "json.loads", "urllib.parse.parse_qs", "flask.request",
    "django.request", "fastapi.Body", "fastapi.Query",
}

_PYTHON_SINKS = {
    "eval": "CWE-95",
    "exec": "CWE-95",
    "compile": "CWE-95",
    "os.system": "CWE-78",
    "os.popen": "CWE-78",
    "subprocess.call": "CWE-78",
    "subprocess.run": "CWE-78",
    "subprocess.Popen": "CWE-78",
    "open": "CWE-73",
    "pickle.loads": "CWE-502",
    "pickle.load": "CWE-502",
    "yaml.load": "CWE-502",
    "marshal.loads": "CWE-502",
    "shelve.open": "CWE-502",
    "__import__": "CWE-95",
    "getattr": "CWE-913",
    "setattr": "CWE-913",
    "format": "CWE-134",
    "% s": "CWE-134",
    "cursor.execute": "CWE-89",
    "raw_input": "CWE-20",
    "render_template_string": "CWE-94",
    "send_file": "CWE-73",
    "redirect": "CWE-601",
}

_JS_SINKS = {
    r"eval\s*\(": "CWE-95",
    r"new\s+Function\s*\(": "CWE-95",
    r"child_process\.exec\s*\(": "CWE-78",
    r"execSync\s*\(": "CWE-78",
    r"innerHTML\s*=": "CWE-79",
    r"document\.write\s*\(": "CWE-79",
    r"dangerouslySetInnerHTML": "CWE-79",
    r"__proto__": "CWE-1321",
    r"res\.redirect\s*\(": "CWE-601",
    r"require\s*\(\s*req\b": "CWE-706",
    r"fs\.readFile\s*\(": "CWE-73",
    r"path\.join\s*\(": "CWE-22",
    r"serialize\s*\(": "CWE-502",
    r"deserialize\s*\(": "CWE-502",
    r"\.query\s*\(": "CWE-89",
}

_SECURITY_FILE_PATTERNS = [
    "auth", "login", "password", "token", "session", "crypto",
    "cipher", "ssl", "tls", "secret", "key", "permission", "acl",
    "admin", "sudo", "privilege", "sql", "query", "database",
    "upload", "download", "file", "path", "directory",
]


def map_attack_surface(repo_dir: str) -> dict:
    """
    Comprehensive attack surface mapping — used by Hermes recon phase.
    Returns structured data about entry points, sinks, and security-critical areas.
    """
    entry_points = []
    dangerous_sinks = []
    security_files = []
    crypto_ops = []
    auth_flows = []
    deser_points = []
    ext_deps = []

    # --- Python files ---
    for py_file in glob.glob(f"{repo_dir}/**/*.py", recursive=True):
        if "site-packages" in py_file or ".tox" in py_file or "node_modules" in py_file:
            continue
        rel = os.path.relpath(py_file, repo_dir)

        if any(p in rel.lower() for p in _SECURITY_FILE_PATTERNS):
            security_files.append(rel)

        try:
            source = open(py_file).read()
            lines = source.splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            for sink, cwe in _PYTHON_SINKS.items():
                if sink in stripped and not stripped.startswith("#"):
                    dangerous_sinks.append({
                        "file": rel, "line": i,
                        "sink": sink, "cwe": cwe,
                        "snippet": stripped[:120],
                    })

            if any(src in stripped for src in ["@app.route", "@router.", "def get(", "def post(", "def put(", "def delete(", "async def "]):
                entry_points.append({"file": rel, "line": i, "snippet": stripped[:100]})

            if any(kw in stripped.lower() for kw in ["hashlib", "hmac", "aes", "rsa", "des", "md5", "sha1", "random.random()"]):
                crypto_ops.append({"file": rel, "line": i, "snippet": stripped[:100]})
                if "md5" in stripped.lower() or "sha1" in stripped.lower() or "random.random" in stripped.lower():
                    crypto_ops[-1]["warning"] = "weak_crypto"

            if any(kw in stripped.lower() for kw in ["pickle.load", "yaml.load(", "marshal.load", "jsonpickle"]):
                deser_points.append({"file": rel, "line": i, "snippet": stripped[:100]})

    # --- JS/TS files ---
    for js_file in glob.glob(f"{repo_dir}/**/*.js", recursive=True):
        if "node_modules" in js_file or ".min." in js_file:
            continue
        rel = os.path.relpath(js_file, repo_dir)
        if any(p in rel.lower() for p in _SECURITY_FILE_PATTERNS):
            security_files.append(rel)
        try:
            source = open(js_file).read()
            lines = source.splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines, 1):
            for pattern, cwe in _JS_SINKS.items():
                if re.search(pattern, line):
                    dangerous_sinks.append({
                        "file": rel, "line": i,
                        "sink": pattern[:30], "cwe": cwe,
                        "snippet": line.strip()[:120],
                    })

    # --- Dependencies ---
    for req_file in ["requirements.txt", "package.json", "go.mod", "Gemfile", "Cargo.toml"]:
        fpath = os.path.join(repo_dir, req_file)
        if os.path.exists(fpath):
            try:
                content = open(fpath).read()
                if req_file == "package.json":
                    data = json.loads(content)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    ext_deps.extend(list(deps.keys())[:30])
                else:
                    ext_deps.extend([l.strip().split("==")[0].split(">=")[0]
                                     for l in content.splitlines() if l.strip() and not l.startswith("#")][:30])
            except Exception:
                pass

    return {
        "entry_points": entry_points[:30],
        "dangerous_sinks": dangerous_sinks[:50],
        "security_critical_files": list(set(security_files))[:20],
        "external_dependencies": ext_deps[:30],
        "crypto_operations": crypto_ops[:15],
        "authentication_flows": auth_flows[:10],
        "deserialization_points": deser_points[:10],
        "summary": {
            "entry_points": len(entry_points),
            "dangerous_sinks": len(dangerous_sinks),
            "security_files": len(set(security_files)),
            "deser_risks": len(deser_points),
            "crypto_issues": sum(1 for c in crypto_ops if c.get("warning")),
        },
    }


def run_taint_analysis(repo_dir: str, focus_files: list[str] = None) -> dict:
    """
    Full taint analysis: find flows from sources to sinks.
    Returns a list of confirmed taint flows with CWE classification.
    """
    flows = []

    search_files = []
    if focus_files:
        search_files = [os.path.join(repo_dir, f) for f in focus_files if f.endswith(".py")]
    else:
        search_files = glob.glob(f"{repo_dir}/**/*.py", recursive=True)
        search_files = [f for f in search_files
                        if "site-packages" not in f and ".tox" not in f and "test_" not in f]

    for py_file in search_files[:50]:
        rel = os.path.relpath(py_file, repo_dir)
        try:
            source = open(py_file).read()
            tree = ast.parse(source)
        except Exception:
            continue

        tainted_vars: dict[str, int] = {}
        lines = source.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                func_str = _node_to_str(node.value.func)
                if any(src in func_str for src in _PYTHON_SOURCES):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            tainted_vars[target.id] = node.lineno

            if isinstance(node, ast.Call):
                func_str = _node_to_str(node.func)
                matched_sink = next((s for s in _PYTHON_SINKS if s in func_str), None)
                if matched_sink:
                    for arg in node.args:
                        arg_str = _node_to_str(arg)
                        if isinstance(arg, ast.Name) and arg.id in tainted_vars:
                            flows.append(TaintFlow(
                                source=f"tainted_var:{arg.id}",
                                sink=matched_sink,
                                path=[arg.id, matched_sink],
                                file_path=rel,
                                source_line=tainted_vars[arg.id],
                                sink_line=node.lineno,
                                cwe_candidates=[_PYTHON_SINKS[matched_sink]],
                                confidence=0.8,
                            ))
                        elif isinstance(arg, ast.JoinedStr):
                            for val in ast.walk(arg):
                                if isinstance(val, ast.Name) and val.id in tainted_vars:
                                    flows.append(TaintFlow(
                                        source=f"fstring:{val.id}",
                                        sink=matched_sink,
                                        path=[val.id, "f-string", matched_sink],
                                        file_path=rel,
                                        source_line=tainted_vars[val.id],
                                        sink_line=node.lineno,
                                        cwe_candidates=[_PYTHON_SINKS[matched_sink], "CWE-134"],
                                        confidence=0.7,
                                    ))

    return {
        "flows_found": len(flows),
        "flows": [
            {
                "source": f.source, "sink": f.sink,
                "file": f.file_path,
                "source_line": f.source_line, "sink_line": f.sink_line,
                "cwes": f.cwe_candidates, "confidence": f.confidence,
                "path": " → ".join(f.path),
            }
            for f in sorted(flows, key=lambda x: x.confidence, reverse=True)[:20]
        ],
        "high_confidence_flows": sum(1 for f in flows if f.confidence >= 0.75),
        "unique_cwes": list(set(cwe for f in flows for cwe in f.cwe_candidates)),
    }


def _node_to_str(node) -> str:
    try:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{_node_to_str(node.value)}.{node.attr}"
        return ""
    except Exception:
        return ""
