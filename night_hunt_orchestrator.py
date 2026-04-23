"""
Rhodawk AI — Night Hunter orchestrator (Masterplan §3, §9 Week 2).

End-to-end loop for autonomous bug-bounty hunting:

    SCOPE INGEST   → scope_parser_mcp / bounty_gateway
    TARGET SELECT  → score by recency, breadth, tech-match, competition
    RECON          → subdomain_enum + httpx + wayback + shodan
    HUNT           → nuclei + zap + sqlmap + jwt-analyzer + cors-analyzer
                     + (optional) browser-agent for authenticated flows
    VALIDATE       → adversarial 3-model consensus + reproducibility filter
    REPORT         → per-platform draft submission + Telegram briefing

Designed to **never auto-submit** in the first 50 cycles — the operator
reviews and approves every finding via the Gradio Night Hunter tab or
the OpenClaw ``approve-finding`` skill.

This module is heavy on graceful degradation: every external dependency
(MCP server, scanner binary, LLM endpoint) is wrapped in try/except so a
missing tool downgrades the cycle quality but never crashes it.

Public surface:

    run_night_cycle(...)        → NightCycleReport
    schedule_loop(start_hour=23) → blocking heartbeat scheduler
    start_in_background()        → daemon thread for app.py
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

LOG = logging.getLogger("rhodawk.night_hunter")

REPORT_DIR = Path(os.getenv("NIGHT_HUNTER_REPORTS", "/data/night_reports"))
REPORT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PLATFORMS = (
    os.getenv("NIGHT_HUNTER_PLATFORMS", "hackerone,bugcrowd,intigriti")
    .lower()
    .split(",")
)
DEFAULT_HOUR = int(os.getenv("NIGHT_HUNTER_HOUR", "23"))
MORNING_HOUR = int(os.getenv("NIGHT_HUNTER_MORNING_HOUR", "6"))
P1_FLOOR = int(os.getenv("NIGHT_HUNTER_P1_FLOOR", "5000"))
P2_FLOOR = int(os.getenv("NIGHT_HUNTER_P2_FLOOR", "1000"))
MAX_TARGETS = int(os.getenv("NIGHT_HUNTER_MAX_TARGETS", "3"))


# ─── Data shapes ────────────────────────────────────────────────────────────
@dataclass
class TargetProfile:
    program: str
    platform: str
    domains: list[str] = field(default_factory=list)
    api_endpoints: list[str] = field(default_factory=list)
    mobile_apps: list[str] = field(default_factory=list)
    p1_bounty: int = 0
    p2_bounty: int = 0
    tech_stack: list[str] = field(default_factory=list)
    score: float = 0.0


@dataclass
class HuntFinding:
    id: str
    title: str
    severity: str
    cvss: float
    target: str
    program: str
    platform: str
    description: str
    reproduction: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    detector: str = ""
    confidence: float = 0.0
    consensus: dict[str, Any] = field(default_factory=dict)
    draft_submission: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NightCycleReport:
    cycle_id: str
    started_at: str
    finished_at: str = ""
    platforms: list[str] = field(default_factory=list)
    targets: list[TargetProfile] = field(default_factory=list)
    findings: list[HuntFinding] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "platforms": self.platforms,
            "targets": [asdict(t) for t in self.targets],
            "findings": [f.to_dict() for f in self.findings],
            "errors": list(self.errors),
            "notes": list(self.notes),
            "summary": self.summary(),
        }

    def summary(self) -> dict[str, Any]:
        sev_counts: dict[str, int] = {}
        for f in self.findings:
            sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1
        return {
            "targets": len(self.targets),
            "findings": len(self.findings),
            "by_severity": sev_counts,
            "errors": len(self.errors),
        }


# ─── Scope ingestion ────────────────────────────────────────────────────────
def _ingest_scope(platforms: Iterable[str]) -> list[TargetProfile]:
    """
    Try every available scope source. Falls back to a static demo list when
    no API tokens are configured so the loop is testable in dev.
    """
    profiles: list[TargetProfile] = []

    # Preferred: existing bounty_gateway helpers (HackerOne / Bugcrowd / Intigriti)
    try:
        import bounty_gateway  # type: ignore
        if hasattr(bounty_gateway, "list_active_programs"):
            for plat in platforms:
                try:
                    raw = bounty_gateway.list_active_programs(plat)  # type: ignore[attr-defined]
                    for p in raw or []:
                        profiles.append(TargetProfile(
                            program=p.get("name") or p.get("handle") or "unknown",
                            platform=plat,
                            domains=list(p.get("scope") or []),
                            api_endpoints=list(p.get("api") or []),
                            mobile_apps=list(p.get("mobile") or []),
                            p1_bounty=int(p.get("p1_bounty") or 0),
                            p2_bounty=int(p.get("p2_bounty") or 0),
                            tech_stack=list(p.get("tech") or []),
                        ))
                except Exception as exc:  # noqa: BLE001
                    LOG.warning("scope ingest failed for %s: %s", plat, exc)
    except Exception as exc:  # noqa: BLE001
        LOG.debug("bounty_gateway unavailable: %s", exc)

    # Secondary: scope_parser_mcp on disk if the gateway is empty
    if not profiles:
        try:
            from mythos.mcp import scope_parser_mcp  # type: ignore
            for plat in platforms:
                if hasattr(scope_parser_mcp, "list_programs"):
                    raw = scope_parser_mcp.list_programs(plat)  # type: ignore[attr-defined]
                    for p in raw or []:
                        profiles.append(TargetProfile(
                            program=str(p.get("handle", "unknown")),
                            platform=plat,
                            domains=list(p.get("scope_domains") or []),
                            p1_bounty=int(p.get("p1") or 0),
                            p2_bounty=int(p.get("p2") or 0),
                        ))
        except Exception as exc:  # noqa: BLE001
            LOG.debug("scope_parser_mcp unavailable: %s", exc)

    # Final fallback so dev loops have *something* to chew on.
    if not profiles:
        profiles.append(TargetProfile(
            program="demo-program",
            platform="hackerone",
            domains=["example.com"],
            p1_bounty=10000,
            p2_bounty=2500,
            tech_stack=["nginx", "node"],
        ))

    return profiles


def _filter_by_floor(profiles: list[TargetProfile]) -> list[TargetProfile]:
    return [p for p in profiles if p.p1_bounty >= P1_FLOOR or p.p2_bounty >= P2_FLOOR]


def _score_targets(profiles: list[TargetProfile]) -> list[TargetProfile]:
    for p in profiles:
        recency = 1.0  # placeholder until bounty_gateway exposes last_payout
        breadth = min(len(p.domains) + len(p.api_endpoints) + len(p.mobile_apps), 25) / 25
        money   = (p.p1_bounty + 0.4 * p.p2_bounty) / 50_000
        p.score = round(0.45 * money + 0.35 * breadth + 0.20 * recency, 4)
    profiles.sort(key=lambda p: p.score, reverse=True)
    return profiles


# ─── Recon ──────────────────────────────────────────────────────────────────
def _safe_call(label: str, fn, *args, **kwargs) -> Any:
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        LOG.warning("%s failed: %s", label, exc)
        return None


def _recon(target: TargetProfile) -> dict[str, Any]:
    out: dict[str, Any] = {"subdomains": [], "alive": [], "wayback_urls": [], "shodan": []}
    if not target.domains:
        return out
    root = target.domains[0]

    try:
        from mythos.mcp import subdomain_enum_mcp  # type: ignore
        out["subdomains"] = _safe_call("subdomain_enum", subdomain_enum_mcp.enumerate, root) or []
    except Exception as exc:  # noqa: BLE001
        LOG.debug("subdomain_enum_mcp not loaded: %s", exc)

    try:
        from mythos.mcp import httpx_probe_mcp  # type: ignore
        hosts = out["subdomains"] or [root]
        out["alive"] = _safe_call("httpx_probe", httpx_probe_mcp.probe, hosts) or []
    except Exception as exc:  # noqa: BLE001
        LOG.debug("httpx_probe_mcp not loaded: %s", exc)

    try:
        from mythos.mcp import wayback_mcp  # type: ignore
        out["wayback_urls"] = _safe_call("wayback", wayback_mcp.urls, root) or []
    except Exception as exc:  # noqa: BLE001
        LOG.debug("wayback_mcp not loaded: %s", exc)

    try:
        from mythos.mcp import shodan_mcp  # type: ignore
        out["shodan"] = _safe_call("shodan", shodan_mcp.lookup, root) or []
    except Exception as exc:  # noqa: BLE001
        LOG.debug("shodan_mcp not loaded: %s", exc)

    return out


# ─── Hunt ────────────────────────────────────────────────────────────────────
_DETECTORS = (
    "nuclei", "zap-active", "sqlmap", "jwt-analyzer",
    "cors-analyzer", "openapi-analyzer", "prototype-pollution",
)


def _hunt(target: TargetProfile, recon: dict[str, Any]) -> list[HuntFinding]:
    findings: list[HuntFinding] = []
    hosts = recon.get("alive") or target.domains or []
    if not hosts:
        return findings

    # The actual scanner orchestration lives in the per-MCP modules; we call
    # them through tiny shim helpers so that missing scanners just skip.
    for host in hosts[:8]:
        for detector in _DETECTORS:
            raw = _safe_call(detector, _run_detector, detector, host)
            if not raw:
                continue
            for r in raw:
                fid = uuid.uuid4().hex[:10]
                findings.append(HuntFinding(
                    id=fid,
                    title=str(r.get("title") or detector),
                    severity=str(r.get("severity") or "info").lower(),
                    cvss=float(r.get("cvss") or 0.0),
                    target=str(r.get("url") or host),
                    program=target.program,
                    platform=target.platform,
                    description=str(r.get("description") or ""),
                    reproduction=list(r.get("reproduction") or []),
                    evidence=dict(r.get("evidence") or {}),
                    detector=detector,
                    confidence=float(r.get("confidence") or 0.5),
                ))
    return findings


def _run_detector(detector: str, host: str) -> list[dict[str, Any]]:
    """
    Thin dispatcher. Each block tries to import the matching MCP/scanner and
    returns ``[{title, severity, cvss, ...}]`` lists. Missing tools => [].
    """
    if detector == "nuclei":
        try:
            from mythos.mcp import web_security_mcp  # type: ignore
            return list(web_security_mcp.run_nuclei(host) or [])
        except Exception:  # noqa: BLE001
            return []
    if detector == "zap-active":
        try:
            from mythos.mcp import web_security_mcp  # type: ignore
            if hasattr(web_security_mcp, "run_zap"):
                return list(web_security_mcp.run_zap(host) or [])
        except Exception:  # noqa: BLE001
            return []
    if detector == "sqlmap":
        try:
            from mythos.mcp import web_security_mcp  # type: ignore
            if hasattr(web_security_mcp, "run_sqlmap"):
                return list(web_security_mcp.run_sqlmap(host) or [])
        except Exception:  # noqa: BLE001
            return []
    if detector == "jwt-analyzer":
        try:
            from mythos.mcp import jwt_analyzer_mcp  # type: ignore
            return list(jwt_analyzer_mcp.scan_host(host) or [])
        except Exception:  # noqa: BLE001
            return []
    if detector == "cors-analyzer":
        try:
            from mythos.mcp import cors_analyzer_mcp  # type: ignore
            return list(cors_analyzer_mcp.scan_host(host) or [])
        except Exception:  # noqa: BLE001
            return []
    if detector == "openapi-analyzer":
        try:
            from mythos.mcp import openapi_analyzer_mcp  # type: ignore
            return list(openapi_analyzer_mcp.scan_host(host) or [])
        except Exception:  # noqa: BLE001
            return []
    if detector == "prototype-pollution":
        try:
            from mythos.mcp import prototype_pollution_mcp  # type: ignore
            return list(prototype_pollution_mcp.scan_host(host) or [])
        except Exception:  # noqa: BLE001
            return []
    return []


# ─── Validation: adversarial 3-model consensus ───────────────────────────────
def _validate(findings: list[HuntFinding]) -> list[HuntFinding]:
    if not findings:
        return findings
    try:
        from architect import godmode_consensus  # type: ignore
        for f in findings:
            verdict = _safe_call("consensus", godmode_consensus.review_finding, f.to_dict())
            if isinstance(verdict, dict):
                f.consensus = verdict
                if verdict.get("severity"):
                    f.severity = str(verdict["severity"]).lower()
                if verdict.get("cvss"):
                    f.cvss = float(verdict["cvss"])
                if verdict.get("confidence"):
                    f.confidence = float(verdict["confidence"])
    except Exception as exc:  # noqa: BLE001
        LOG.debug("godmode_consensus unavailable: %s", exc)

    # Drop low-conviction noise.
    keep: list[HuntFinding] = []
    for f in findings:
        if f.severity in ("info", "informational") and f.cvss < 4.0:
            continue
        if f.confidence < 0.45 and not f.consensus:
            continue
        keep.append(f)
    return keep


# ─── Reporting ──────────────────────────────────────────────────────────────
PLATFORM_TEMPLATES: dict[str, str] = {
    "hackerone": (
        "## Summary\n{description}\n\n## Steps to Reproduce\n{steps}\n\n"
        "## Impact\nCVSS {cvss} ({severity}). {impact}\n\n## Suggested Fix\n{fix}\n"
    ),
    "bugcrowd": (
        "**Bug Type:** {title}\n**Severity:** {severity} (CVSS {cvss})\n\n"
        "**Description**\n{description}\n\n**Reproduction**\n{steps}\n\n"
        "**Impact**\n{impact}\n"
    ),
    "intigriti": (
        "Title: {title}\nSeverity: {severity}\nCVSS: {cvss}\n\n"
        "Description:\n{description}\n\nSteps:\n{steps}\n\nImpact:\n{impact}\n"
    ),
}


def _draft_submission(f: HuntFinding) -> str:
    template = PLATFORM_TEMPLATES.get(f.platform, PLATFORM_TEMPLATES["hackerone"])
    steps = "\n".join(f"{i+1}. {s}" for i, s in enumerate(f.reproduction)) or "(see evidence)"
    impact = f.consensus.get("impact") if isinstance(f.consensus, dict) else ""
    fix = f.consensus.get("remediation") if isinstance(f.consensus, dict) else ""
    return template.format(
        title=f.title,
        description=f.description or "(generated)",
        steps=steps,
        cvss=f.cvss,
        severity=f.severity,
        impact=impact or "(operator: confirm blast radius before submission)",
        fix=fix or "(operator: add remediation guidance)",
    )


def _persist(report: NightCycleReport) -> Path:
    report.finished_at = datetime.now(timezone.utc).isoformat()
    fname = f"night_{report.cycle_id}.json"
    path = REPORT_DIR / fname
    try:
        path.write_text(json.dumps(report.to_dict(), indent=2, default=str))
    except Exception as exc:  # noqa: BLE001
        LOG.warning("persist failed: %s", exc)
    return path


def _briefing(report: NightCycleReport) -> str:
    lines = [
        f"🦅 Rhodawk Night Hunter — cycle {report.cycle_id}",
        f"Targets: {len(report.targets)} | Findings: {len(report.findings)}",
    ]
    if report.findings:
        lines.append("")
        for f in report.findings[:5]:
            lines.append(f"• [{f.severity.upper()} CVSS {f.cvss}] {f.title} — {f.target}")
        if len(report.findings) > 5:
            lines.append(f"… and {len(report.findings) - 5} more in the dashboard.")
    else:
        lines.append("No findings tonight. Quiet sky.")
    return "\n".join(lines)


def _notify(report: NightCycleReport) -> None:
    text = _briefing(report)
    # Telegram via embodied_bridge / notifier.
    try:
        from architect import embodied_bridge  # type: ignore
        embodied_bridge.emit_status(text, level="night_report")
    except Exception as exc:  # noqa: BLE001
        LOG.debug("embodied_bridge unavailable: %s", exc)
    try:
        import notifier  # type: ignore
        if hasattr(notifier, "notify"):
            notifier.notify(text)  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        LOG.debug("notifier unavailable: %s", exc)


# ─── Public entry point ─────────────────────────────────────────────────────
def run_night_cycle(
    *,
    platforms: Iterable[str] | None = None,
    max_targets: int = MAX_TARGETS,
) -> NightCycleReport:
    """Execute one full hunting cycle and return the report."""
    cycle_id = uuid.uuid4().hex[:12]
    report = NightCycleReport(
        cycle_id=cycle_id,
        started_at=datetime.now(timezone.utc).isoformat(),
        platforms=list(platforms or DEFAULT_PLATFORMS),
    )
    LOG.info("night cycle %s starting (platforms=%s)", cycle_id, report.platforms)

    try:
        profiles = _ingest_scope(report.platforms)
        profiles = _filter_by_floor(profiles)
        profiles = _score_targets(profiles)
        report.targets = profiles[:max_targets]
        report.notes.append(f"selected {len(report.targets)} of {len(profiles)} qualifying programs")
    except Exception as exc:  # noqa: BLE001
        LOG.exception("scope phase crashed: %s", exc)
        report.errors.append(f"scope:{exc}")
        return _finalise(report)

    for tgt in report.targets:
        try:
            recon = _recon(tgt)
            findings = _hunt(tgt, recon)
            findings = _validate(findings)
            for f in findings:
                f.draft_submission = _draft_submission(f)
            report.findings.extend(findings)
        except Exception as exc:  # noqa: BLE001
            LOG.exception("target %s crashed: %s", tgt.program, exc)
            report.errors.append(f"target:{tgt.program}:{exc}")

    return _finalise(report)


def _finalise(report: NightCycleReport) -> NightCycleReport:
    _persist(report)
    _notify(report)
    LOG.info("night cycle %s done — %s", report.cycle_id, report.summary())
    return report


# ─── Heartbeat scheduler ────────────────────────────────────────────────────
def _seconds_until(hour: int) -> float:
    now = datetime.now()
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target = target.replace(day=now.day + 1) if now.day < 28 else target
    return max(60.0, (target - now).total_seconds())


def schedule_loop(start_hour: int = DEFAULT_HOUR) -> None:
    """Blocking scheduler. Runs forever; safe to launch in a daemon thread."""
    LOG.info("night-hunt scheduler armed — first run at %02d:00", start_hour)
    while True:
        sleep_s = _seconds_until(start_hour)
        LOG.info("next night cycle in %.1f h", sleep_s / 3600)
        time.sleep(sleep_s)
        try:
            run_night_cycle()
        except Exception as exc:  # noqa: BLE001
            LOG.exception("night cycle crashed: %s", exc)
            time.sleep(900)


_THREAD: threading.Thread | None = None


def start_in_background(start_hour: int | None = None) -> threading.Thread:
    """Idempotent — only one scheduler thread is ever started."""
    global _THREAD
    if _THREAD and _THREAD.is_alive():
        return _THREAD
    hour = start_hour if start_hour is not None else DEFAULT_HOUR
    _THREAD = threading.Thread(
        target=schedule_loop, args=(hour,), name="night-hunt", daemon=True
    )
    _THREAD.start()
    LOG.info("night-hunt background thread started (hour=%d)", hour)
    return _THREAD


# CLI entry — useful for manual smoke tests.
if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    rep = run_night_cycle()
    print(json.dumps(rep.summary(), indent=2))
