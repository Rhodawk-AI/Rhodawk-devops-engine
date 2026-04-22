"""
ARCHITECT — autonomous "night-mode" loop (§5.2 of the Masterplan).

Phase schedule (operator-local time):
    18:00 → scope ingestion (HackerOne / Bugcrowd / Intigriti)
    18:30 → reconnaissance fan-out per top target
    20:00 → vulnerability hunt — 5 specialist agents in parallel
    04:00 → report drafting
    08:00 → operator review handoff (Telegram nudge)

The scheduler is opt-in (``ARCHITECT_NIGHTMODE=1``).  It never executes any
submission action; the operator remains the final gate on every report.
"""

from __future__ import annotations

import datetime as _dt
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from . import embodied_bridge

LOG = logging.getLogger("architect.nightmode")


@dataclass
class PhaseResult:
    name: str
    started_at: str
    completed_at: str | None = None
    targets: list[str] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    error: str | None = None


def _now() -> str:
    return _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Phase callables (overridable for tests) ─────────────────────────────────

def _phase_scope_ingest() -> list[str]:
    """Pull active programs from every linked bounty platform."""
    targets: list[str] = []
    try:
        from mythos.mcp.scope_parser_mcp import server as scope
        out = scope.call("list_active_programs", {})
        for p in (out or {}).get("programs", []):
            for asset in p.get("in_scope_assets", []):
                targets.append(asset)
    except Exception as exc:  # noqa: BLE001
        LOG.warning("scope ingest failed: %s", exc)
    return targets[: int(os.getenv("ARCHITECT_NIGHTMODE_MAX_TARGETS", "10"))]


def _phase_recon(target: str) -> dict[str, Any]:
    out: dict[str, Any] = {"target": target}
    try:
        from mythos.mcp.subdomain_enum_mcp import server as subs
        out["subdomains"] = subs.call("enumerate", {"target": target}).get("subdomains", [])
    except Exception as exc:  # noqa: BLE001
        out["subdomains_error"] = str(exc)
    try:
        from mythos.mcp.httpx_probe_mcp import server as probe
        out["live_hosts"] = probe.call("probe", {"hosts": out.get("subdomains", [])}).get("live", [])
    except Exception as exc:  # noqa: BLE001
        out["probe_error"] = str(exc)
    try:
        from mythos.mcp.wayback_mcp import server as wb
        out["historical_urls"] = wb.call("snapshots", {"domain": target}).get("urls", [])
    except Exception as exc:  # noqa: BLE001
        out["wayback_error"] = str(exc)
    return out


def _phase_hunt(target: str, recon: dict[str, Any]) -> list[dict]:
    """Run the 5 specialist agents (auth, server-side, logic, infra, api)."""
    findings: list[dict] = []
    # Optional: import the multi-agent Mythos orchestrator for this target.
    try:
        from mythos import build_default_orchestrator
        orch = build_default_orchestrator(max_iterations=2)
        dossier = orch.run_campaign({
            "repo": target, "repo_path": "/tmp/none",
            "languages": ["http"], "frameworks": [], "dependencies": [],
            "harness_dir": f"/tmp/architect/{target}",
            "extra_context": {"recon": recon},
        })
        for it in dossier.get("iterations", []):
            for h in it.get("findings", []):
                findings.append(h)
    except Exception as exc:  # noqa: BLE001
        LOG.warning("hunt failed for %s: %s", target, exc)
    return findings


def _phase_report(findings: list[dict]) -> list[dict]:
    """Filter to ACTS ≥ 0.72 and format for human review."""
    out: list[dict] = []
    for h in findings:
        if h.get("acts_score", 0.0) < float(os.getenv("ARCHITECT_ACTS_GATE", "0.72")):
            continue
        out.append({
            "title": h.get("title", "(untitled)"),
            "severity": h.get("severity", "P3"),
            "cwe": h.get("cwe", "?"),
            "summary": h.get("description", "")[:280],
            "acts_score": h.get("acts_score", 0.0),
        })
    return out


@dataclass
class NightRun:
    started_at: str = field(default_factory=_now)
    finished_at: str | None = None
    phases: list[PhaseResult] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def run_one_cycle() -> NightRun:
    run = NightRun()
    embodied_bridge.emit_status("Night-mode cycle started", "info")

    p1 = PhaseResult(name="scope_ingest", started_at=_now())
    try:
        p1.targets = _phase_scope_ingest()
    except Exception as exc:  # noqa: BLE001
        p1.error = str(exc)
    p1.completed_at = _now()
    run.phases.append(p1)

    all_findings: list[dict] = []
    for tgt in p1.targets:
        pr = PhaseResult(name=f"recon[{tgt}]", started_at=_now())
        recon = _phase_recon(tgt)
        pr.completed_at = _now()
        run.phases.append(pr)

        ph = PhaseResult(name=f"hunt[{tgt}]", started_at=_now())
        try:
            ph.findings = _phase_hunt(tgt, recon)
            all_findings.extend(ph.findings)
        except Exception as exc:  # noqa: BLE001
            ph.error = str(exc)
        ph.completed_at = _now()
        run.phases.append(ph)

    rep = PhaseResult(name="report", started_at=_now())
    rep.findings = _phase_report(all_findings)
    rep.completed_at = _now()
    run.phases.append(rep)

    run.summary = {
        "targets": len(p1.targets),
        "raw_findings": len(all_findings),
        "qualified_findings": len(rep.findings),
    }
    run.finished_at = _now()
    embodied_bridge.emit_status(
        f"Night-mode complete — {run.summary['qualified_findings']} reviewable finding(s) "
        f"across {run.summary['targets']} target(s)", "info")
    return run


def _next_run_time(hour: int) -> float:
    now = _dt.datetime.now()
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += _dt.timedelta(days=1)
    return target.timestamp()


def schedule_loop(start_hour: int | None = None) -> None:
    """Daemon loop: runs ``run_one_cycle`` once per day at start_hour:00 local."""
    if not os.getenv("ARCHITECT_NIGHTMODE", "0").lower() in ("1", "true", "yes", "on"):
        LOG.info("ARCHITECT night-mode disabled (set ARCHITECT_NIGHTMODE=1)")
        return
    hour = int(start_hour if start_hour is not None
               else os.getenv("ARCHITECT_NIGHTMODE_HOUR", "18"))
    LOG.info("ARCHITECT night-mode scheduler armed for %02d:00 daily", hour)
    while True:
        wake = _next_run_time(hour)
        time.sleep(max(1.0, wake - time.time()))
        try:
            run_one_cycle()
        except Exception as exc:  # noqa: BLE001
            LOG.exception("Night-mode cycle crashed: %s", exc)
            embodied_bridge.emit_status(f"Night-mode crashed: {exc}", "error")


def start_in_background() -> None:
    threading.Thread(target=schedule_loop, daemon=True, name="architect-nightmode").start()
