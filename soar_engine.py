"""
Rhodawk EmbodiedOS — SOAR Playbook Engine (Gap 12)
===================================================
Executes YAML-defined Security Orchestration / Automation / Response
playbooks against findings produced by ``conviction_engine`` and the
Hermes orchestrator.

INV-027: SOAR playbook execution is logged append-only.

Design
------
* Playbooks live under ``$SOAR_PLAYBOOK_DIR`` (default
  ``/opt/soar_playbooks``) as ``*.yml`` / ``*.yaml`` files.
* Each playbook is a list of steps. Supported step kinds:
    - ``http_post``    — fan-out webhook (Slack/Teams/Pager)
    - ``shell``        — bounded subprocess (allow-list of binaries)
    - ``threat_graph`` — promote finding into the threat graph
    - ``tool``         — invoke a hermes_orchestrator tool by name
    - ``log``          — pure audit-log step
* Selection is by ``trigger`` block (severity ≥ X, cwe in {…}, tags …).
* Every step's start + end is appended to ``$SOAR_LOG_PATH`` (JSONL,
  open(..., "a")) — never rewritten, never truncated.

Public surface
--------------
    SOAREngine()
        .reload()                          load all YAMLs from disk
        .matching_playbooks(finding)       list[Playbook]
        .run_playbook(pb, finding)         PlaybookRun
        .process_finding(finding)          run all matching playbooks

YAML example (minimal)
----------------------
    name: critical-rce-pager
    trigger:
      severity_min: HIGH
      cwe_in: [CWE-77, CWE-78, CWE-94]
    steps:
      - kind: log
        message: "RCE class finding detected — paging on-call"
      - kind: http_post
        url: ${SOAR_PAGER_WEBHOOK}
        body:
          text: "[Rhodawk] {{ finding.title }} — {{ finding.severity }}"
      - kind: threat_graph
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import shlex
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

LOG = logging.getLogger("rhodawk.soar")

PLAYBOOK_DIR = os.getenv("SOAR_PLAYBOOK_DIR", "/opt/soar_playbooks")
SOAR_LOG_PATH = os.getenv("SOAR_LOG_PATH", "/data/soar_executions.jsonl")
SOAR_HTTP_TIMEOUT = int(os.getenv("SOAR_HTTP_TIMEOUT", "20"))
SOAR_SHELL_TIMEOUT = int(os.getenv("SOAR_SHELL_TIMEOUT", "120"))
SOAR_SHELL_ALLOWLIST = {
    b.strip()
    for b in os.getenv(
        "SOAR_SHELL_ALLOWLIST",
        "echo,curl,jq,git,trivy,grype,syft,osv-scanner,nuclei",
    ).split(",")
    if b.strip()
}

_SEVERITY_RANK = {
    "INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4,
}


# ──────────────────────────────────────────────────────────────────────
# Data models
# ──────────────────────────────────────────────────────────────────────

@dataclass
class PlaybookStepResult:
    kind: str
    ok: bool
    started_at: str
    finished_at: str
    detail: Any = None
    error: Optional[str] = None


@dataclass
class PlaybookRun:
    playbook: str
    finding_id: str
    started_at: str
    finished_at: str
    steps: list[PlaybookStepResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.steps)


@dataclass
class Playbook:
    name: str
    trigger: dict
    steps: list[dict]
    source_path: str


# ──────────────────────────────────────────────────────────────────────
# Trigger matching
# ──────────────────────────────────────────────────────────────────────

def _finding_attr(finding: Any, key: str, default: Any = None) -> Any:
    if isinstance(finding, dict):
        return finding.get(key, default)
    return getattr(finding, key, default)


def _matches(trigger: dict, finding: Any) -> bool:
    sev = str(_finding_attr(finding, "severity", "MEDIUM")).upper()
    cwe = str(_finding_attr(finding, "cwe_id", _finding_attr(finding, "cwe", ""))).upper()
    tags = _finding_attr(finding, "tags", []) or []
    if "severity_min" in trigger:
        need = _SEVERITY_RANK.get(str(trigger["severity_min"]).upper(), 0)
        have = _SEVERITY_RANK.get(sev, 0)
        if have < need:
            return False
    if "cwe_in" in trigger:
        wanted = {str(c).upper() for c in trigger["cwe_in"]}
        if cwe not in wanted:
            return False
    if "tags_any" in trigger:
        wanted_t = {str(t).lower() for t in trigger["tags_any"]}
        have_t = {str(t).lower() for t in tags}
        if not (wanted_t & have_t):
            return False
    return True


# ──────────────────────────────────────────────────────────────────────
# Step executors (small, sandboxed)
# ──────────────────────────────────────────────────────────────────────

def _render(template: Any, finding: Any) -> Any:
    """Tiny `{{ finding.field }}` renderer. No Jinja dep."""
    if isinstance(template, dict):
        return {k: _render(v, finding) for k, v in template.items()}
    if isinstance(template, list):
        return [_render(v, finding) for v in template]
    if not isinstance(template, str):
        return template
    s = template
    # ${ENV} substitution
    for k, v in os.environ.items():
        s = s.replace("${" + k + "}", v)
    # {{ finding.x }} substitution
    if "{{" in s:
        for token in [t.strip() for t in s.split("{{")[1:]]:
            if "}}" not in token:
                continue
            expr, _ = token.split("}}", 1)
            expr = expr.strip()
            if expr.startswith("finding."):
                key = expr.split(".", 1)[1]
                val = _finding_attr(finding, key, "")
                s = s.replace("{{ " + expr + " }}", str(val))
                s = s.replace("{{" + expr + "}}", str(val))
    return s


def _exec_log(step: dict, finding: Any) -> PlaybookStepResult:
    msg = _render(step.get("message", ""), finding)
    LOG.info("[SOAR.log] %s", msg)
    return _wrap_step_ok("log", detail={"message": msg})


def _exec_http_post(step: dict, finding: Any) -> PlaybookStepResult:
    import requests  # local — already in requirements.txt
    url = _render(step.get("url", ""), finding)
    body = _render(step.get("body", {}), finding)
    headers = _render(step.get("headers", {}), finding) or {}
    if not url:
        return _wrap_step_err("http_post", "missing url")
    try:
        r = requests.post(url, json=body, headers=headers, timeout=SOAR_HTTP_TIMEOUT)
        return _wrap_step_ok(
            "http_post",
            detail={"status": r.status_code, "len": len(r.text or "")},
        ) if r.ok else _wrap_step_err("http_post", f"HTTP {r.status_code}")
    except Exception as exc:  # noqa: BLE001
        return _wrap_step_err("http_post", str(exc)[:300])


def _exec_shell(step: dict, finding: Any) -> PlaybookStepResult:
    cmd_raw = _render(step.get("cmd", ""), finding)
    if not cmd_raw:
        return _wrap_step_err("shell", "missing cmd")
    parts = shlex.split(cmd_raw)
    if not parts:
        return _wrap_step_err("shell", "empty cmd")
    binary = os.path.basename(parts[0])
    if binary not in SOAR_SHELL_ALLOWLIST:
        return _wrap_step_err(
            "shell", f"binary {binary!r} not in SOAR_SHELL_ALLOWLIST"
        )
    try:
        proc = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=SOAR_SHELL_TIMEOUT,
            check=False,
        )
        return _wrap_step_ok(
            "shell",
            detail={
                "rc": proc.returncode,
                "stdout_tail": (proc.stdout or "")[-400:],
                "stderr_tail": (proc.stderr or "")[-400:],
            },
        ) if proc.returncode == 0 else _wrap_step_err(
            "shell",
            f"rc={proc.returncode} stderr={(proc.stderr or '')[-300:]}",
        )
    except subprocess.TimeoutExpired:
        return _wrap_step_err("shell", f"timeout after {SOAR_SHELL_TIMEOUT}s")
    except Exception as exc:  # noqa: BLE001
        return _wrap_step_err("shell", str(exc)[:300])


def _exec_threat_graph(step: dict, finding: Any) -> PlaybookStepResult:
    try:
        import threat_graph  # type: ignore
        db = threat_graph.get_db()
        promote = getattr(db, "record_finding", None) or getattr(
            db, "upsert_finding", None
        )
        if promote is None:
            return _wrap_step_err("threat_graph", "no promote method on ThreatGraphDB")
        promote(finding)
        return _wrap_step_ok("threat_graph", detail={"promoted": True})
    except Exception as exc:  # noqa: BLE001
        return _wrap_step_err("threat_graph", str(exc)[:300])


def _exec_tool(step: dict, finding: Any) -> PlaybookStepResult:
    tool_name = step.get("tool")
    args = _render(step.get("args", {}), finding) or {}
    if not tool_name:
        return _wrap_step_err("tool", "missing tool name")
    try:
        from hermes_orchestrator import _dispatch_tool  # late import — avoids cycles

        class _Anon:
            session_id = "soar"
            repo_dir = args.get("repo_dir", "")
            phase = "soar"
            findings: list = []

        result = _dispatch_tool(tool_name, args, _Anon())
        return _wrap_step_ok(
            "tool", detail={"tool": tool_name, "result_excerpt": str(result)[:400]}
        )
    except Exception as exc:  # noqa: BLE001
        return _wrap_step_err("tool", str(exc)[:300])


def _wrap_step_ok(kind: str, detail: Any = None) -> PlaybookStepResult:
    now = _utcnow()
    return PlaybookStepResult(
        kind=kind, ok=True, started_at=now, finished_at=now, detail=detail
    )


def _wrap_step_err(kind: str, error: str) -> PlaybookStepResult:
    now = _utcnow()
    return PlaybookStepResult(
        kind=kind, ok=False, started_at=now, finished_at=now, error=error
    )


def _utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_EXECUTORS = {
    "log": _exec_log,
    "http_post": _exec_http_post,
    "shell": _exec_shell,
    "threat_graph": _exec_threat_graph,
    "tool": _exec_tool,
}


# ──────────────────────────────────────────────────────────────────────
# Engine
# ──────────────────────────────────────────────────────────────────────

class SOAREngine:
    """Loads YAML playbooks and dispatches them against findings.

    INV-027: every PlaybookRun is appended to ``SOAR_LOG_PATH`` as a
    single JSON line. Failures to append are logged but never raised
    so a missing log volume cannot stop the security pipeline.
    """

    def __init__(self, playbook_dir: str | None = None):
        self._dir = playbook_dir or PLAYBOOK_DIR
        self._playbooks: list[Playbook] = []
        self._lock = threading.Lock()
        self._loaded = False

    # ── lifecycle ────────────────────────────────────────────────────

    def reload(self) -> int:
        """Re-read every YAML in the playbook dir. Returns count."""
        try:
            import yaml  # type: ignore  (PyYAML — pulled in via gradio/transformers tree)
        except Exception as exc:  # noqa: BLE001
            LOG.warning("PyYAML not installed — SOAREngine cannot load: %s", exc)
            with self._lock:
                self._playbooks = []
                self._loaded = True
            return 0

        loaded: list[Playbook] = []
        if not os.path.isdir(self._dir):
            LOG.info("SOAR playbook dir %s missing — no playbooks loaded.", self._dir)
            with self._lock:
                self._playbooks = loaded
                self._loaded = True
            return 0
        for path in sorted(Path(self._dir).glob("*.y*ml")):
            try:
                with open(path) as fh:
                    raw = yaml.safe_load(fh) or {}
                if not isinstance(raw, dict):
                    continue
                loaded.append(
                    Playbook(
                        name=str(raw.get("name", path.stem)),
                        trigger=raw.get("trigger", {}) or {},
                        steps=list(raw.get("steps", []) or []),
                        source_path=str(path),
                    )
                )
            except Exception as exc:  # noqa: BLE001
                LOG.warning("Failed to load SOAR playbook %s: %s", path, exc)
        with self._lock:
            self._playbooks = loaded
            self._loaded = True
        LOG.info("SOAREngine loaded %d playbook(s) from %s", len(loaded), self._dir)
        return len(loaded)

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.reload()

    # ── selection + execution ───────────────────────────────────────

    def matching_playbooks(self, finding: Any) -> list[Playbook]:
        self._ensure_loaded()
        with self._lock:
            return [pb for pb in self._playbooks if _matches(pb.trigger, finding)]

    def run_playbook(self, pb: Playbook, finding: Any) -> PlaybookRun:
        run = PlaybookRun(
            playbook=pb.name,
            finding_id=str(_finding_attr(finding, "finding_id", "anon")),
            started_at=_utcnow(),
            finished_at="",
        )
        for step in pb.steps:
            kind = str(step.get("kind", "")).lower()
            executor = _EXECUTORS.get(kind)
            if executor is None:
                run.steps.append(_wrap_step_err(kind or "unknown", "unsupported kind"))
                continue
            try:
                run.steps.append(executor(step, finding))
            except Exception as exc:  # noqa: BLE001
                run.steps.append(_wrap_step_err(kind, str(exc)[:300]))
        run.finished_at = _utcnow()
        self._append_log(run)
        return run

    def process_finding(self, finding: Any) -> list[PlaybookRun]:
        """Run every matching playbook for a finding. Returns all runs."""
        runs: list[PlaybookRun] = []
        for pb in self.matching_playbooks(finding):
            try:
                runs.append(self.run_playbook(pb, finding))
            except Exception as exc:  # noqa: BLE001
                LOG.warning("SOAR playbook %s crashed: %s", pb.name, exc)
        return runs

    # ── append-only log (INV-027) ───────────────────────────────────

    def _append_log(self, run: PlaybookRun) -> None:
        try:
            os.makedirs(os.path.dirname(SOAR_LOG_PATH) or ".", exist_ok=True)
            payload = {
                "playbook": run.playbook,
                "finding_id": run.finding_id,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "ok": run.ok,
                "steps": [
                    {
                        "kind": s.kind,
                        "ok": s.ok,
                        "started_at": s.started_at,
                        "finished_at": s.finished_at,
                        "detail": s.detail,
                        "error": s.error,
                    }
                    for s in run.steps
                ],
            }
            with open(SOAR_LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, default=str) + "\n")
        except Exception as exc:  # noqa: BLE001
            LOG.warning("SOAR append-only log write failed: %s", exc)


_DEFAULT_ENGINE: SOAREngine | None = None


def get_default_engine() -> SOAREngine:
    """Process-wide singleton. Lazily loaded."""
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        _DEFAULT_ENGINE = SOAREngine()
        _DEFAULT_ENGINE.reload()
    return _DEFAULT_ENGINE


__all__ = [
    "SOAREngine",
    "Playbook",
    "PlaybookRun",
    "PlaybookStepResult",
    "get_default_engine",
]
